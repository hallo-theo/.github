# notion — workspace pages & databases

**What it is:** the org's Notion workspace (dashboards, boards, master-data
mirrors). Reference writers: `notion-workers` (sync workers),
`front-door/api/src/front_door_api/tickets.py` (fire-and-forget card sync).

## Code side (worker tickets)

- Plain `httpx` against `https://api.notion.com/v1` with
  `Notion-Version: 2025-09-03` — no SDK needed (see `tickets.py`).
- Fire-and-forget doctrine when Notion is observability, not control: a
  Notion failure must never fail or slow the app's own request path.
- Rate limit ~3 req/s per integration — batch and cache; never poll hot.

## Entitlement

The SDLC app lane shares **one dedicated integration**: `theo-sdlc-apps`.
Its token lives in the platform secret `sdlc-apps-notion-token`
(`project-shepherd-494112`; shell is terraform-owned in
`terraform/integrations.tf`, the version is added by a workspace admin).

**Automated** (when `notion` is declared on the form and Accepted): the
newborn's `terraform/entitlements.tf` grants its own `<slug>-run` SA
`secretAccessor` on that shared secret — the app reads the token at runtime
with its own identity; nothing is mounted, nothing is copied.

**Where apps put their pages:** under the shared **"SDLC Apps" parent page**
— children created via the API inherit the integration's access, so no
per-app sharing is ever needed.

- Parent page id: `3f0ac28a49f980b8ab28df0c192ac43e` ("SDLC Apps";
  verified 2026-10-05: read + create + archive round-trip green).

**One-time setup (workspace admin, once ever):**

1. Create the internal integration `theo-sdlc-apps` in Notion.
2. Create the parent page "SDLC Apps" and share it with that integration.
3. Add the integration token as a version of `sdlc-apps-notion-token`.
4. Replace the parent page id placeholder above (same PR discipline: docs
   move with reality).

**The boundary (read before sharing anything else):** every SDLC app holding
this grant can read and write the whole "SDLC Apps" subtree — that shared
blast radius is the deliberate trade for zero per-app ceremony, and it is
acceptable because the subtree contains only platform-app data. Org
databases (Objekte, Standort, Jahresabschluss, …) are NOT visible to this
integration; a pitch that needs one is a Risks/escalations entry, and
sharing that single database with `theo-sdlc-apps` is a deliberate,
recorded human act — it entitles the WHOLE lane, so prefer modelling with
plain id fields (e.g. store the warehouse `objectId` as text) over
relations into org databases.
