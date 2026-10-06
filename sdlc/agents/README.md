# Agent registry

`agents.yaml` is the org's declared inventory of agents — every identity that
acts on hallo theo's behalf, which lane it belongs to, who owns it, and how it
pays for LLM calls. It is the source of truth for **teams and virtual keys on
the LiteLLM gateway** (`llm-internal.theo.tools`): lanes are LiteLLM teams
with monthly budgets, agents get keys aliased `<lane>--<agent>`.

Why a file and not the admin UI: the UI writes straight to the gateway's
Postgres with no review, no history and no drift detection. This file is
reviewed like code, and `sync.py` makes the gateway match it.

## The contract

- **Adding an agent happens in the PR that creates it.** An agent without a
  registry entry is drift, and the drift report will say so.
- **The sync never revokes.** `sync.py` creates and updates; anything on the
  gateway the registry doesn't explain is *reported*, and removal stays a
  deliberate human act. Rotation = create the new key, migrate the consumer,
  watch the old key's spend flatline, then revoke by hand.
- **Bypasses are listed, not hidden.** An agent on a direct Anthropic key is
  registered with `llm.via: anthropic-direct` so the gap is visible until the
  migration lands.

## Running the sync

```bash
# offline validation (what CI runs on every PR touching sdlc/agents/)
uv run sdlc/agents/sync.py --check

# dry run against the gateway — prints the plan and the drift report
export LITELLM_MASTER_KEY=$(gcloud secrets versions access latest \
  --project=theo-prod-llmgw-178085 --secret=internal-litellm-master-key)
uv run sdlc/agents/sync.py \
  --iap-sa agent-registry-sync@project-shepherd-494112.iam.gserviceaccount.com

# execute — new key values land in Secret Manager (llm-key-<alias>), never stdout
uv run sdlc/agents/sync.py --iap-sa ... --apply --sm-project project-shepherd-494112
```

The admin API sits behind IAP (Entra workforce pool). Machines pass it with a
service-account signed JWT in `Proxy-Authorization` — that is what `--iap-sa`
mints (requires `roles/iam.serviceAccountTokenCreator` on the SA, granted in
`terraform/agent_registry.tf`). The LiteLLM master key rides in
`Authorization` as usual. The SA's IAP grant lives with the gateway owners in
theo-tools-platform.
