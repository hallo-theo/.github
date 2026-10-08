#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6", "requests>=2.31"]
# ///
"""Sync the agent registry (agents.yaml) to the LiteLLM gateway.

The registry is the source of truth. The sync is additive and idempotent:
it creates missing teams (lanes) and keys, updates team budgets, and reports
everything on the gateway the registry does not explain. It NEVER revokes,
deletes or regenerates anything — removing access is a deliberate human act.

Modes:
  --check          offline: validate agents.yaml and exit (CI gate)
  (default)        dry run: print the plan, change nothing
  --apply          execute the plan

Auth (apply/dry-run):
  LITELLM_MASTER_KEY      env, required — LiteLLM admin auth
  --iap-sa EMAIL          mint an IAP signed JWT for this service account
                          (caller needs roles/iam.serviceAccountTokenCreator
                          on it) and send it as Proxy-Authorization. Without
                          this flag the request goes out with the master key
                          only, which works when the caller is already inside
                          an IAP session or the route is not IAP-gated.

New key values are written straight to Secret Manager (--sm-project,
secret name llm-key-<alias>) and are never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
import yaml

REGISTRY = Path(__file__).parent / "agents.yaml"
SKILLS = Path(__file__).parent / "skills.yaml"
VALID_VIA = {"gateway", "anthropic-direct", "none", "unknown"}


class GatewayError(RuntimeError):
    """A gateway call failed. Raised so a caller can decide: abort, or skip one item."""


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_registry() -> dict:
    data = yaml.safe_load(REGISTRY.read_text())
    problems = []
    lanes = data.get("lanes") or {}
    agents = data.get("agents") or []
    if not (data.get("gateway") or {}).get("base_url"):
        problems.append("gateway.base_url missing")
    for lane, cfg in lanes.items():
        if not isinstance(cfg.get("max_budget_usd_month"), (int, float)):
            problems.append(f"lane {lane}: max_budget_usd_month missing")
    seen = set()
    for agent in agents:
        name, lane = agent.get("name"), agent.get("lane")
        if not name or not lane:
            problems.append(f"agent entry without name/lane: {agent}")
            continue
        if lane not in lanes:
            problems.append(f"agent {name}: undeclared lane {lane}")
        if (name, lane) in seen:
            problems.append(f"duplicate agent {lane}--{name}")
        seen.add((name, lane))
        via = (agent.get("llm") or {}).get("via")
        if via not in VALID_VIA:
            problems.append(f"agent {name}: llm.via must be one of {sorted(VALID_VIA)}, got {via!r}")
        groups = (agent.get("llm") or {}).get("mcp_access_groups", [])
        if not (isinstance(groups, list) and all(isinstance(g, str) for g in groups)):
            problems.append(f"agent {name}: llm.mcp_access_groups must be a list of strings")
        skills = agent.get("skills", [])
        if not (isinstance(skills, list) and all(isinstance(s, str) for s in skills)):
            problems.append(f"agent {name}: skills must be a list of strings (repo paths)")
        if not agent.get("owner"):
            problems.append(f"agent {name}: owner missing")
    if problems:
        fail("agents.yaml invalid:\n  - " + "\n  - ".join(problems))
    return data


def load_skills() -> dict:
    """skills.yaml — the SKILL.md bundles published to the gateway's skill hub."""
    if not SKILLS.exists():
        return {"skills": []}
    data = yaml.safe_load(SKILLS.read_text()) or {}
    problems = []
    seen = set()
    for s in data.get("skills") or []:
        if not s.get("name") or not s.get("path") or not s.get("repo"):
            problems.append(f"skill entry needs name, repo and path: {s}")
            continue
        if s["repo"].count("/") != 1 or s["repo"].startswith("http"):
            problems.append(f"skill {s['name']}: repo must be owner/name, got {s['repo']!r}")
        if s["name"] in seen:
            problems.append(f"duplicate skill {s['name']}")
        seen.add(s["name"])
    if problems:
        fail("skills.yaml invalid:\n  - " + "\n  - ".join(problems))
    return data


def iap_jwt(service_account: str, audience: str) -> str:
    now = int(time.time())
    claims = {"iss": service_account, "sub": service_account, "aud": audience,
              "iat": now, "exp": now + 3600}
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = Path(tmp) / "claims.json", Path(tmp) / "signed.jwt"
        inp.write_text(json.dumps(claims))
        subprocess.run(
            ["gcloud", "iam", "service-accounts", "sign-jwt",
             f"--iam-account={service_account}", str(inp), str(out)],
            check=True, capture_output=True, text=True)
        return out.read_text().strip()


class Gateway:
    def __init__(self, base_url: str, master_key: str, iap_token: str | None):
        self.base = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {master_key}"}
        if iap_token:
            self.headers["Proxy-Authorization"] = f"Bearer {iap_token}"

    def _req(self, method: str, path: str, **kwargs) -> dict:
        resp = requests.request(method, f"{self.base}{path}",
                                headers=self.headers, timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise GatewayError(f"{method} {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def teams(self) -> dict[str, dict]:
        rows = self._req("GET", "/team/list")
        return {t["team_alias"]: t for t in rows if t.get("team_alias")}

    def keys(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        page = 1
        while True:
            data = self._req("GET", "/key/list",
                             params={"page": page, "size": 100, "return_full_object": "true"})
            for k in data.get("keys", []):
                if isinstance(k, dict) and k.get("key_alias"):
                    out[k["key_alias"]] = k
            if page >= int(data.get("total_pages") or 1):
                return out
            page += 1

    def create_team(self, alias: str, budget: float) -> str:
        team = self._req("POST", "/team/new", json={
            "team_alias": alias, "max_budget": budget, "budget_duration": "30d"})
        return team["team_id"]

    def update_team_budget(self, team_id: str, budget: float) -> None:
        self._req("POST", "/team/update", json={"team_id": team_id, "max_budget": budget})

    def create_key(self, alias: str, team_id: str, metadata: dict,
                   mcp_access_groups: list[str]) -> str:
        body: dict = {"key_alias": alias, "team_id": team_id, "metadata": metadata}
        if mcp_access_groups:
            body["object_permission"] = {"mcp_access_groups": mcp_access_groups}
        data = self._req("POST", "/key/generate", json=body)
        return data["key"]

    def agents(self) -> dict[str, dict]:
        rows = self._req("GET", "/v1/agents")
        rows = rows if isinstance(rows, list) else rows.get("agents", [])
        return {a["agent_name"]: a for a in rows if a.get("agent_name")}

    def skills(self) -> dict[str, dict]:
        """Skill hub = the Claude Code plugin marketplace behind the UI's Skills page."""
        data = self._req("GET", "/claude-code/plugins")
        return {p["name"]: p for p in data.get("plugins", []) if p.get("name")}

    def create_skill(self, name: str, repo_url: str, path: str, description: str) -> None:
        self._req("POST", "/claude-code/plugins", json={
            "name": name,
            "description": description,
            "source": {"source": "git-subdir", "url": repo_url, "path": path},
        })

    def create_agent(self, agent_name: str, card: dict) -> str:
        data = self._req("POST", "/v1/agents", json={
            "agent_name": agent_name, "agent_card_params": card})
        return data.get("agent_id", "")


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text]
    return "".join(keep).strip("-")[:48] or "skill"


def agent_card(agent: dict) -> dict:
    """Build a minimal A2A agent card from a registry entry. No url — this is a
    governance catalog entry, not a live endpoint. Card skills come from the
    registry's skills inventory (repo paths), or a single capability skill
    derived from the description when none are declared."""
    skills = [
        {"id": _slug(s), "name": s[:64], "description": s, "tags": [agent["lane"]]}
        for s in agent.get("skills", [])
    ] or [{
        "id": _slug(agent["name"]),
        "name": agent["name"],
        "description": agent.get("description", agent["name"]),
        "tags": [agent["lane"]],
    }]
    return {
        "name": agent["name"],
        "description": agent.get("description", agent["name"]),
        "version": "1.0.0",
        "capabilities": {},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "skills": skills,
    }


def store_key(sm_project: str, alias: str, value: str) -> None:
    secret = f"llm-key-{alias}"
    exists = subprocess.run(
        ["gcloud", "secrets", "describe", secret, f"--project={sm_project}"],
        capture_output=True).returncode == 0
    if not exists:
        subprocess.run(["gcloud", "secrets", "create", secret, f"--project={sm_project}",
                        "--replication-policy=user-managed", "--locations=europe-west3"],
                       check=True, capture_output=True)
    subprocess.run(["gcloud", "secrets", "versions", "add", secret,
                    f"--project={sm_project}", "--data-file=-"],
                   input=value.encode(), check=True, capture_output=True)
    print(f"  stored key value in Secret Manager: {sm_project}/{secret}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate agents.yaml offline and exit")
    parser.add_argument("--apply", action="store_true", help="execute the plan (default: dry run)")
    parser.add_argument("--iap-sa", help="service account email for the IAP signed JWT")
    parser.add_argument("--iap-aud", help="JWT audience override (default: <base_url>/*)")
    parser.add_argument("--sm-project", help="GCP project that receives new key values as secrets")
    parser.add_argument("--strict", action="store_true", help="exit 1 when unexplained drift is found")
    args = parser.parse_args()

    registry = load_registry()
    skills = load_skills()
    # Every other gateway call still aborts the run — only per-skill creates are
    # tolerated (see the skill loop below).
    print(f"agents.yaml valid: {len(registry['agents'])} agents, {len(registry['lanes'])} lanes")
    print(f"skills.yaml valid: {len(skills.get('skills') or [])} skills")
    if args.check:
        return

    master_key = os.environ.get("LITELLM_MASTER_KEY") or fail("LITELLM_MASTER_KEY not set")
    base_url = os.environ.get("LITELLM_BASE_URL") or registry["gateway"]["base_url"]
    iap_token = iap_jwt(args.iap_sa, args.iap_aud or base_url + "/*") if args.iap_sa else None
    gw = Gateway(base_url, master_key, iap_token)

    if args.apply and not args.sm_project:
        fail("--apply requires --sm-project: new key values go to Secret Manager, never stdout")

    teams, keys = gw.teams(), gw.keys()
    wanted_keys = {f"{a['lane']}--{a['name']}": a for a in registry["agents"]
                   if a["llm"]["via"] == "gateway"}
    plan_notes, drift = [], []

    for lane, cfg in registry["lanes"].items():
        budget = float(cfg["max_budget_usd_month"])
        team = teams.get(lane)
        if team is None:
            plan_notes.append(f"CREATE team {lane} (budget {budget}/30d)")
            if args.apply:
                teams[lane] = {"team_id": gw.create_team(lane, budget), "team_alias": lane}
        elif team.get("max_budget") != budget:
            plan_notes.append(f"UPDATE team {lane} budget {team.get('max_budget')} -> {budget}")
            if args.apply:
                gw.update_team_budget(team["team_id"], budget)

    for alias, agent in sorted(wanted_keys.items()):
        if alias in keys:
            continue
        plan_notes.append(f"CREATE key {alias} (team {agent['lane']}, owner {agent['owner']})")
        if args.apply:
            value = gw.create_key(alias, teams[agent["lane"]]["team_id"], {
                "agent": agent["name"], "lane": agent["lane"],
                "owner": agent["owner"], "managed_by": "sdlc/agents/sync.py"},
                agent["llm"].get("mcp_access_groups", []))
            store_key(args.sm_project, alias, value)

    # A2A agent catalog: register each of OUR agents (all lanes except
    # vendor-tools, which are third-party tools, not agents we govern) as a
    # url-less governance entry. The card is descriptive only — no live A2A
    # endpoint yet; this is the central inventory the gateway UI shows.
    gw_agents = gw.agents()
    for agent in registry["agents"]:
        if agent["lane"] == "vendor-tools":
            continue
        name = f"{agent['lane']}--{agent['name']}"
        if name in gw_agents:
            continue
        plan_notes.append(f"CREATE agent {name} (catalog entry, no endpoint)")
        if args.apply:
            gw.create_agent(name, agent_card(agent))

    # Skill hub: publish each declared SKILL.md bundle as a repo reference.
    gw_skills = gw.skills()
    for s in skills.get("skills") or []:
        if s["name"] in gw_skills:
            continue
        plan_notes.append(f"CREATE skill {s['name']} ({s['repo']}/{s['path']})")
        if args.apply:
            # One unpublishable skill must not strand the rest: report and continue.
            try:
                gw.create_skill(s["name"], f"https://github.com/{s['repo']}", s["path"],
                                s.get("description", ""))
            except GatewayError as exc:
                plan_notes[-1] += f"  !! FAILED: {exc}"

    drift += [f"gateway team not in registry: {t}" for t in teams if t not in registry["lanes"]]
    drift += [f"gateway key not in registry: {k}" for k in keys if k not in wanted_keys]
    registry_agent_names = {f"{a['lane']}--{a['name']}" for a in registry["agents"]}
    drift += [f"gateway agent not in registry: {n}" for n in gw_agents if n not in registry_agent_names]
    declared_skills = {s["name"] for s in (skills.get("skills") or [])}
    drift += [f"gateway skill not in registry: {n}" for n in gw_skills if n not in declared_skills]
    drift += [f"agent off-gateway (llm.via={a['llm']['via']}): {a['lane']}--{a['name']}"
              for a in registry["agents"] if a["llm"]["via"] in ("anthropic-direct", "unknown")]

    mode = "APPLIED" if args.apply else "DRY RUN (use --apply)"
    print(f"\n== plan [{mode}] ==")
    print("\n".join(f"  {n}" for n in plan_notes) if plan_notes else "  nothing to do — in sync")
    print("\n== drift report (never auto-fixed) ==")
    print("\n".join(f"  {d}" for d in drift) if drift else "  none")
    if drift and args.strict:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except GatewayError as exc:
        fail(str(exc))
