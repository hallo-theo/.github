# The headless provisioner's GCP identity. It replays the /front-door steps
# in CI (provision.yml in this repo): terraform for the newborn app, Windmill
# wiring, secrets. Powerful by necessity — the containment is that ONLY
# workflows running in hallo-theo/.github can assume it (WIF attribute
# condition below), and .github/** is excluded from automerge, so the
# provisioner's own definition can never self-merge.

resource "google_service_account" "provisioner" {
  account_id   = "provisioner"
  display_name = "SDLC headless provisioner"
  description  = "Runs newborn-app terraform + wiring for Front Door accepts. Assumable only via WIF from hallo-theo/.github workflows."
}

# Each role maps to a concrete step of newborn-app provisioning:
#   workloadIdentityPoolAdmin  → create the per-repo WIF provider
#   serviceAccountAdmin        → create the app's deploy SA
#   projectIamAdmin            → grant the deploy SA its three project roles
#   run.admin                  → bootstrap the Cloud Run service
#   artifactregistry.admin     → create the per-repo AR repo
#   secretmanager.admin        → create <slug>-frontend-service-secret + bindings
resource "google_project_iam_member" "provisioner_roles" {
  for_each = toset([
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/artifactregistry.admin",
    "roles/secretmanager.admin",
  ])
  project = local.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.provisioner.email}"
}

# Newborn-app terraform state lives in the shared tfstate bucket.
resource "google_storage_bucket_iam_member" "provisioner_tfstate" {
  bucket = "${local.project}-tfstate"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.provisioner.email}"
}

# WIF: GitHub Actions in hallo-theo/.github — and ONLY there — may mint
# tokens for this SA. Mirrors the per-app provider shape (github-pool is
# pre-existing and deliberately not managed here).
resource "google_iam_workload_identity_pool_provider" "provisioner" {
  workload_identity_pool_id          = "github-pool"
  workload_identity_pool_provider_id = "sdlc-provisioner"
  display_name                       = "SDLC provisioner (.github)"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.ref"        = "assertion.ref"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == 'hallo-theo/.github'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "provisioner_wif" {
  service_account_id = google_service_account.provisioner.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${local.project_number}/locations/global/workloadIdentityPools/github-pool/attribute.repository/hallo-theo/.github"
}

# Container for the theo-provisioner GitHub App private key — the front-door
# API mints dispatch tokens from it on Accept. The VALUE is added out-of-band
# (console paste) so the pem never enters terraform state.
resource "google_secret_manager_secret" "provisioner_app_key" {
  secret_id = "provisioner-app-private-key"
  replication {
    auto {}
  }
}

# front-door-api runs on the default compute SA today (known deviation).
resource "google_secret_manager_secret_iam_member" "front_door_reads_app_key" {
  secret_id = google_secret_manager_secret.provisioner_app_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.project_number}-compute@developer.gserviceaccount.com"
}
