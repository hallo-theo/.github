# Integration entitlements — the provisioner's grant rights (Phase 3.5).
#
# The provisioner APPLIES per-app entitlements from the systems list the
# approver Accepted; to do that it needs grant rights on the systems
# themselves. One resource per cataloged system (sdlc/integrations/).
#
# NOTE: per-app grants are not wired yet — newborns still run on the shared
# default compute SA and granting that would entitle every app at once. This
# file only positions the provisioner so the grant becomes a provision-time
# terraform step the moment per-app runtime SAs land (Cloud Run stack work).

# bigquery: dataset-level owner on the master-data warehouse, so the
# provisioner can add/remove per-app dataViewer members.
resource "google_bigquery_dataset_iam_member" "provisioner_masterdata_owner" {
  project    = "hallotheo-443008"
  dataset_id = "master_data"
  role       = "roles/bigquery.dataOwner"
  member     = "serviceAccount:${google_service_account.provisioner.email}"
}
