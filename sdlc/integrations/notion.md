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

Notion access is **manual by design** — there is no IAM to terraform:

1. A workspace admin creates (or reuses) an internal integration token and
   stores it in Secret Manager (`project-shepherd-494112`); the newborn's
   Cloud Run service mounts it as an env var.
2. A human must **share each required page/database with the integration**
   in the Notion UI — this is the entitlement act, page by page. Unshared
   pages are invisible to the token no matter what the code does.

The roadmap's integration ticket must therefore name the exact pages/DBs to
share, and the journey escalates (`needs_human`) until sharing is confirmed.
Never reuse another product's token scope-creep style — one integration per
product lane (the Feedback-Hub-App lesson, applied to Notion).
