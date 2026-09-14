# SDLC platform infrastructure — the resources the AI-Native SDLC itself
# stands on (provisioner identity, its WIF trust, its secrets). Per-app
# infrastructure lives in each app repo's own terraform/; this file owns only
# what belongs to the platform. Changes land via PR here and are applied with
# `terraform apply` from this directory.

terraform {
  required_version = ">= 1.7"
  backend "gcs" {
    bucket = "project-shepherd-494112-tfstate"
    prefix = "sdlc-platform"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

locals {
  project        = "project-shepherd-494112"
  project_number = "757287535499"
  region         = "europe-west3"
}

provider "google" {
  project = local.project
  region  = local.region
}
