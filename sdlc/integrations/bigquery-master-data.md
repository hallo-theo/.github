# bigquery — the master-data warehouse

**What it is:** `hallotheo-443008.master_data` — the org's building/object
warehouse (source of truth mirrored to Notion "Objekte · Stammdaten";
`objectId` is the join key across systems). Reference reader:
`object-finder` (`api/src/object_finder_api/sources/bigquery.py`).

## Code side (worker tickets)

- Dependency: `google-cloud-bigquery` in `api/pyproject.toml`.
- Client: default credentials (`bigquery.Client(project=<app project>)`) —
  queries are billed to the app's own project, the dataset is only read.
- Fully-qualify tables: `` `hallotheo-443008.master_data.<table>` ``.
- Read-only by doctrine: apps never write to `master_data`.
- pyright: `import google.cloud.bigquery as bigquery` (the
  `from google.cloud import bigquery` form does not type-resolve).

## Verified schema map (2026-09-29 — do NOT guess table names)

There is **no `objects` table** (found live: portfolio-explorer 502'd on it).
The object registry is:

| What you want | Where it really is |
|---|---|
| The objects | `properties` — key `md_property_id`, display `name`; **live rows have `status_id = 100`** |
| City | `addresses` with `entity_table = 'Properties'`, joined on `entity_id = md_property_id`; take the latest row per entity (`ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY updated_at DESC)`) |
| Unit count | `COUNT(*)` of `units` grouped by `md_property_id` |
| Cross-system ids | `_property_id_mappings` (impower/hubspot/domus/customer-app ids) |
| **Standort** | **NOT in the warehouse.** Standort (the managing team) lives in the Notion Objekte world — a feature needing it is a Risks/escalations entry, never a derived guess from city. |

Reference implementation with these exact joins:
`object-finder/api/src/object_finder_api/sources/bigquery.py`.

## Entitlement

The app's runtime service account needs:

1. `roles/bigquery.dataViewer` **on the dataset**
   `hallotheo-443008:master_data` (dataset-level, not project-level), and
2. `roles/bigquery.jobUser` on the app's own project (to run query jobs).

Grant path — **automatic**: when `bigquery` was declared on the form and
Accepted, the provisioner writes `terraform/entitlements.tf` into the
newborn (dataset `dataViewer` + project `jobUser` for the app's `<slug>-run`
SA) and applies it at provision time; destroy removes it with the app. The
provisioner can do this because it holds `roles/bigquery.dataOwner` on the
dataset (platform `terraform/integrations.tf`). Never grant to the shared
default compute SA — that would entitle every app at once.
