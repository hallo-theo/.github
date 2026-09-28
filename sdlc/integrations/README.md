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

## Current status (2026-09-28, honest)

Newborn apps still run on the **shared default compute service account**
(golden-path deviation, fix queued with the Cloud Run stack work). Granting
that SA a dataset would entitle *every* app at once — so automatic
per-app IAM grants are deliberately **not** wired yet. Until the per-app
runtime SA lands:

- the decomposer plans integration tickets from the catalog (code side), and
- any entitlement is granted **manually by the pitch owner** per the entry's
  "Entitlement" section — the provisioner's own grant rights are already in
  place (`terraform/integrations.tf`).

| System (form value) | Entry | Auto-entitlement |
|---|---|---|
| `bigquery` | [bigquery-master-data.md](bigquery-master-data.md) | pending per-app SA |
| `notion` | [notion.md](notion.md) | manual by design (page shares) |
| `impower`, `domus`, `hubspot`, `dvelop`, `sendgrid`, `windmill` | not yet cataloged | escalate |
