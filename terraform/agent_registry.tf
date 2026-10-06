# The agent registry's sync identity (sdlc/agents/sync.py). Its only power is
# passing IAP in front of the LiteLLM admin API: the IAP grant itself lives
# with the gateway owners (theo-tools-platform, backend internal-litellm-admin)
# so each team's repo changes only its own resources. It deliberately has NO
# roles in this project — the LiteLLM master key, supplied by the operator at
# runtime, is what authorizes the management calls.

resource "google_service_account" "agent_registry_sync" {
  account_id   = "agent-registry-sync"
  display_name = "Agent registry sync"
  description  = "Passes IAP to the LiteLLM admin API for sdlc/agents/sync.py. No project roles."
}

# Operators who may run the sync: signing the IAP JWT requires tokenCreator on
# this SA. Deliberately individuals, not a group — running the sync writes
# teams/keys on the gateway.
resource "google_service_account_iam_member" "agent_registry_sync_operators" {
  for_each = toset([
    "user:ali.alkhateeb@hallotheo.de",
  ])
  service_account_id = google_service_account.agent_registry_sync.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = each.value
}
