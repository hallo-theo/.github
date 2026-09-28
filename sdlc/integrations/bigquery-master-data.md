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

## Entitlement

The app's runtime service account needs:

1. `roles/bigquery.dataViewer` **on the dataset**
   `hallotheo-443008:master_data` (dataset-level, not project-level), and
2. `roles/bigquery.jobUser` on the app's own project (to run query jobs).

Grant path: the provisioner SA holds `roles/bigquery.dataOwner` on the
dataset (platform `terraform/integrations.tf`), so once newborns have a
per-app runtime SA the provisioner applies both grants automatically when
`bigquery` was declared + Accepted. Until then: manual grant by the pitch
owner, and ONLY for a per-app SA — never for the shared default compute SA
(that would entitle every app at once).
