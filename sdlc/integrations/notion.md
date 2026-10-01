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

Notion access is **manual by design** — sharing pages has no IAM to
terraform. The split since 2026-10-01:

**Automated** (when `notion` is declared on the form and Accepted): the
provisioner writes into the newborn's `terraform/entitlements.tf` an EMPTY
Secret Manager secret `<slug>-notion-token` plus a `secretAccessor` grant
for the app's own `<slug>-run` SA — so the secret lives and dies with the
app, and only that app can read it.

**Manual** (the actual entitlement act):

1. A workspace admin creates a **new internal integration** for this app
   (one integration per product lane — never a reused token) and adds its
   token as a version of `<slug>-notion-token`.
2. The admin **shares each required page/database with the integration**
   in the Notion UI, page by page. Unshared pages are invisible to the
   token no matter what the code does.

The roadmap's integration ticket must therefore name the exact pages/DBs to
share, and the journey escalates (`needs_human`) until sharing is confirmed.
Never reuse another product's token scope-creep style — one integration per
product lane (the Feedback-Hub-App lesson, applied to Notion).
