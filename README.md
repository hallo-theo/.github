# hallo theo — shared CI/CD definitions

Reusable GitHub Actions workflows and conventions that every hallo theo app
can call into. Goal: each app's CI/CD is **~10–20 lines of YAML**,
delegating to the workflows defined here.

## What's here

| Path | What it is |
|------|------------|
| `.github/workflows/python-ts-pr.yml` | Reusable PR check — Python (uv, ruff, pyright, pytest), TS (npm, tsc, vitest), optional Terraform fmt+validate, optional Docker build sanity. |
| `.github/workflows/python-ts-deploy.yml` | Reusable deploy — pre-flight re-run of PR gates, Docker build + push to Artifact Registry, Cloud Run deploy, optional `wmill app push`. |

## How to adopt in your app

### Stack family

These workflows are for **Python (FastAPI / uv) + TypeScript (Vite / React)** apps,
optionally with Terraform infra and an optional raw_app frontend hosted in Windmill.
Other stacks (Next.js, pure Windmill, Kotlin/Spring, …) get their own reusable
workflows added here as second adopters appear.

### PR workflow

Add `.github/workflows/pr.yml` to your repo:

```yaml
name: PR
on:
  pull_request:
    branches: [main]

concurrency:
  group: pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  ci:
    uses: hallo-theo/.github/.github/workflows/python-ts-pr.yml@main
    with:
      api-path: api                            # omit if no backend
      api-package: object-details-api          # uv workspace package, optional
      app-path: app/object_details.raw_app     # omit if no frontend
      terraform-path: terraform                # omit if no terraform/
      dockerfile: api/Dockerfile               # omit to skip docker build sanity
```

### Deploy workflow (push to main)

Add `.github/workflows/main.yml`:

```yaml
name: Main
on:
  push:
    branches: [main]
  workflow_dispatch:

concurrency:
  group: deploy-prod-${{ github.ref }}
  cancel-in-progress: false   # never kill an in-flight deploy

jobs:
  deploy:
    uses: hallo-theo/.github/.github/workflows/python-ts-deploy.yml@main
    with:
      gcp-project-id:         project-shepherd-494112
      gcp-project-number:     "757287535499"
      gcp-region:             europe-west3
      wif-provider-name:      object-details
      deploy-sa:              object-details-deploy@project-shepherd-494112.iam.gserviceaccount.com
      cloud-run-service:      object-details-api
      artifact-registry-repo: object-details
      image-name:             api
      dockerfile:             api/Dockerfile
      docker-context:         .
      api-path:               api
      api-package:            object-details-api
      app-path:               app/object_details.raw_app
      wmill-workspace:        hallotheo
      wmill-app-path:         f/object_details/app
      wmill-base-url:         https://wm.hallotheo.de
    secrets:
      wmill-token: ${{ secrets.WMILL_TOKEN }}
```

## One-time per-repo setup

### 1. WIF provider + deploy service account

WIF pool `github-pool` is shared org-wide. Each repo gets its own provider
inside that pool (scoped via `assertion.repository ==
"hallo-theo/<your-repo>"`) and its own deploy SA. Substitute `<repo>` and
run as a user with project IAM admin:

```bash
PROJECT=project-shepherd-494112
PROJECT_NUMBER=757287535499
REPO=<your-repo>

# Deploy SA
gcloud iam service-accounts create ${REPO}-deploy \
  --display-name="${REPO} — CI/CD deploy" \
  --project=${PROJECT}

# Roles
for role in roles/artifactregistry.writer roles/iam.serviceAccountUser roles/run.developer; do
  gcloud projects add-iam-policy-binding ${PROJECT} \
    --member="serviceAccount:${REPO}-deploy@${PROJECT}.iam.gserviceaccount.com" \
    --role="$role"
done

# WIF provider scoped to this repo
gcloud iam workload-identity-pools providers create-oidc ${REPO} \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=${PROJECT} \
  --display-name="${REPO}" \
  --description="Trusts GitHub's OIDC issuer, scoped to hallo-theo/${REPO}." \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == 'hallo-theo/${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Bind the WIF "GitHub Actions in this repo" identity to the deploy SA
gcloud iam service-accounts add-iam-policy-binding \
  ${REPO}-deploy@${PROJECT}.iam.gserviceaccount.com \
  --project=${PROJECT} \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/hallo-theo/${REPO}"
```

### 2. GitHub secrets

```bash
# Windmill workspace token, scoped to your repo(s)
gh secret set WMILL_TOKEN --org hallo-theo --visibility selected --repos <your-repo>
```

## Inputs reference

### `python-ts-pr.yml`

| Input | Default | Notes |
|-------|---------|-------|
| `python-version` | `"3.12"` | |
| `node-version`   | `"20"`   | |
| `api-path`       | `""`     | Path to Python source root. Empty = skip backend jobs. |
| `api-package`    | `""`     | uv workspace package, used as `uv run --package <name> pytest …`. Optional. |
| `app-path`       | `""`     | Path to the frontend. Empty = skip frontend jobs. |
| `terraform-path` | `""`     | Path to terraform sources. Empty = skip terraform job. |
| `terraform-version` | `"1.7.5"` | |
| `dockerfile`     | `""`     | Path to Dockerfile. Empty = skip docker build sanity job. |
| `docker-context` | `"."`    | Build context for the docker sanity check. |

### `python-ts-deploy.yml`

| Input | Required | Notes |
|-------|----------|-------|
| `gcp-project-id` | ✅ | |
| `gcp-project-number` | ✅ | Used to build the WIF principal path. |
| `gcp-region` | (default `europe-west3`) | |
| `wif-provider-name` | ✅ | Provider name inside `github-pool`. |
| `deploy-sa` | ✅ | Email of the per-repo deploy SA. |
| `cloud-run-service` | ✅ | Service name to redeploy. |
| `artifact-registry-repo` | ✅ | AR repo name (path between region and image-name). |
| `image-name` | (default `api`) | |
| `dockerfile` | (default `api/Dockerfile`) | |
| `docker-context` | (default `.`) | |
| `api-path` / `api-package` / `app-path` / `python-version` / `node-version` | optional | Same shape as `python-ts-pr.yml` — used by the pre-flight rerun. |
| `wmill-workspace` | (default `hallotheo`) | |
| `wmill-app-path` | required if `app-path` set | E.g. `f/object_details/app`. |
| `wmill-base-url` | required if `app-path` set | E.g. `https://wm.hallotheo.de`. |
| `secrets.wmill-token` | required if `app-path` set | Pass via `secrets: wmill-token: ${{ secrets.WMILL_TOKEN }}`. |

## Conventions across the org

Even repos that *don't* use these reusable workflows (e.g. `beirat-belegpruefung`
which has its own standalone setup) should follow these conventions so the org
stays coherent:

- **Concurrency groups.** PRs cancel in-progress: `group: pr-${{ github.event.pull_request.number }}`. Main deploys don't cancel: `group: deploy-prod-${{ github.ref }}`, `cancel-in-progress: false`.
- **WIF, not service-account keys.** Every repo gets a per-repo provider in the shared `github-pool`, scoped by `assertion.repository`. Per-repo deploy SAs named `<repo>-deploy@…`.
- **Org-level secrets** for things shared across repos (e.g. `WMILL_TOKEN`). Repo-scoped via `--visibility selected --repos …` so they don't leak to repos that shouldn't see them.
- **Belt-and-braces pre-flight on main.** Re-run the PR gates before deploying. Catches force-pushes that bypass review.

## Versioning

Today: `@main` — adopters point at the moving tip. We'll move to `@v1` tags
once enough repos depend on it that breaking changes need a signal.

## Why a `.github` repo

GitHub treats this repo (`hallo-theo/.github`) as the org's default-files
repo: PR templates, issue templates, and the org-profile README all live
here. Reusable workflows aren't org-default magic — they're regular workflow
files that other repos reference via `uses:`. Living in the same repo as the
org defaults just keeps everything shared-and-versioned in one place.
