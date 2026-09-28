# Integration catalog — "Systems it touches" made real

One entry per org system a Front-Door app can declare on the form. Each
entry states: what the system is, how the app's **code** integrates, what
**entitlement** (credential/IAM) it needs, and who grants it.

## The security keystone

**Agents never expand their own access.** The systems list declared on the
form and approved at Accept is the hard boundary:

- Entitlements are applied by the **provisioner** at provision time, from
  the declared list — the Accept click *is* the entitlement approval (the
  approver saw "touches: bigquery, notion" and said yes).
- If the admin agent or a worker discovers the app needs a system that was
  **not** declared, it must NOT work around it (no scraping, no borrowed
  tokens): it records the need under Risks/escalations and the supervisor
  escalates to a human. A new entitlement is a human decision, always.

## Current status (2026-09-28)

Newborns are born with a **per-app runtime SA** (`<slug>-run`, stack
terraform) — entitlements bind that identity, never a shared one. When a
cataloged system was declared on the form and Accepted, the provisioner
writes `terraform/entitlements.tf` into the newborn and applies it at
provision time; `terraform destroy` removes the entitlement with the app.

| System (form value) | Entry | Auto-entitlement |
|---|---|---|
| `bigquery` | [bigquery-master-data.md](bigquery-master-data.md) | ✅ auto at provision (per-app SA) |
| `notion` | [notion.md](notion.md) | manual by design (page shares) |
| `impower`, `domus`, `hubspot`, `dvelop`, `sendgrid`, `windmill` | not yet cataloged | escalate |

Apps born before 2026-09-28 (incl. front-door itself) still run on the
shared default compute SA — migrating them is a separate step.
