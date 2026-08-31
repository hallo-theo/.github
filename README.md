# hallo theo — shared CI/CD definitions

Reusable GitHub Actions workflows and conventions that every hallo theo app
can call into. Goal: each app's CI/CD is **~10–20 lines of YAML**, delegating
to the workflows defined here.

## TL;DR — starting a brand-new hallo theo app

Two paths, pick whichever you prefer. **Both produce the same end state.**

| | Skill path (Claude Code) | Template repo path |
|---|---|---|
| **Trigger** | `/new-app` in Claude Code | `gh repo create --template hallo-theo/template-fastapi-windmill-app` then `bash scripts/bootstrap.sh` |
| **Discoverable via GitHub UI** | ❌ | ✅ "Use this template" button |
| **Requires Claude Code** | ✅ | ❌ |
| **Auto-runs gcloud + Windmill setup** | ✅ | ❌ — prints commands, you copy-paste |
| **Auto-bootstraps Cloud Run + Windmill variables + .env.general** | ✅ | ❌ — same prints |
| **Time** | ~5 min | ~10–15 min |

- **Skill path:** see [`hallotheo-claude-plugins` → `builder-tools` → `new-app`](https://github.com/hallo-theo/hallotheo-claude-plugins/tree/main/plugins/builder-tools/skills/new-app)
- **Template path:** see [`hallo-theo/template-fastapi-windmill-app`](https://github.com/hallo-theo/template-fastapi-windmill-app)

Both wire up the workflow callers documented below. The rest of this README
covers what those workflows actually do, plus the one-time setup commands
(useful for retrofitting an existing repo or troubleshooting).

## What's here

| Path | What it is |
|------|------------|
| `.github/workflows/python-ts-pr.yml` | Reusable PR check — Python (uv, ruff, pyright, pytest), TS (npm, tsc, vitest), optional Terraform fmt+validate, optional Docker build sanity. |
| `.github/workflows/python-ts-deploy.yml` | Reusable deploy — pre-flight re-run of PR gates, Docker build + push to Artifact Registry, Cloud Run deploy, optional `wmill app push`. |
| **[`sdlc/README.md`](sdlc/README.md)** | **The six SDLC stages and the artifact each one commits.** Start here. |
| `sdlc/templates/` | Copy-in templates: `intent.md`, `spec.md`, `plan.md`, `REVIEW.md`. |
| `.github/PULL_REQUEST_TEMPLATE.md` | **Org-wide** PR template — GitHub applies it to every repo without its own. This is where the artifact chain is joined. |

## How to adopt manually (retrofit an existing repo)

If you're not bootstrapping from scratch — say, an existing repo that doesn't
have CI yet, or you want full control over the workflow files — wire it
manually:

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

  # The one required check for this repo. Copy verbatim.
  # `needs` MUST list `ci` plus every caller-local job that should gate a
  # merge — a job missing from this list gates nothing.
  gates-passed:
    needs: [ci]
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Assert every gate ended in success or skipped
        env:
          NEEDS: ${{ toJSON(needs) }}
        run: |
          # `skipped` passes — a section whose path input is empty, or whose
          # code was untouched, has nothing to prove. `cancelled` FAILS: the
          # gate never actually ran, so reporting it green would merge
          # untested code.
          echo "$NEEDS" | jq -r 'to_entries[] | "\(.value.result)\t\(.key)"' | sort
          bad="$(echo "$NEEDS" | jq -r '
            to_entries[]
            | select(.value.result != "success" and .value.result != "skipped")
            | .key')"
          if [ -n "$bad" ]; then
            echo "::error::Gate failed. Jobs not in {success, skipped}:"
            echo "$bad" | while read -r j; do echo "::error::  $j"; done
            exit 1
          fi
          echo "All gates passed."
```

## `gates-passed` — the org's single required check

**Every repo requires exactly one check, named `gates-passed`.** Not `ci`, not
the individual jobs. One name across the whole org is the point: it is what
lets an org-level ruleset gate every repository without per-repo
configuration.

Why it has to live in the caller rather than in the reusable workflow:

- Every job in `python-ts-pr.yml` is conditional (`if: inputs.<path> != ''`),
  so there is no single inner check name that is meaningful for all adopters.
  A repo with no `terraform/` cannot require a `terraform` check.
- Reusable-workflow jobs surface **prefixed** by the caller's job name
  (`ci / python`, `ci / frontend`); caller-local jobs surface **bare**
  (`gates-passed`). `project-shepherd` and `mietanpassungen` already require
  the bare name — matching it keeps one string org-wide.

Two rules that are not obvious:

1. **Never put `paths:` filters on the `pull_request:` trigger** of the
   workflow that owns the required check. If the workflow does not run, the
   check never reports, and every PR sits on *"Expected — waiting for
   status"* forever. Filter inside jobs instead.
2. **`skipped` passes, `cancelled` fails.** Skipped means a section had
   nothing to prove. Cancelled means the gate never ran.

### Turning it on for a repo

```bash
REPO=<your-repo>
gh api -X POST "repos/hallo-theo/$REPO/rulesets" --input - <<'JSON'
{
  "name": "sdlc-floor",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [ { "context": "gates-passed" } ]
      }
    }
  ]
}
JSON
```

`strict_required_status_checks_policy: true` is *"require branches to be up to
date before merging"*. Without it a PR can go green against an older `main`
and merge a combination nothing ever tested. It is currently enabled on zero
repos in this org, which is why it is in the snippet rather than left to
taste.

Do this per repo only until the org-level ruleset exists. **The intended end
state is one org ruleset per repo class, targeted by a custom repository
property** — so a new repo inherits its gate from its class and nobody
configures a repository again. That needs org-admin.

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
    # Required at JOB level (not workflow level) for the reusable workflow's
    # nested jobs to inherit id-token: write for WIF auth.
    permissions:
      id-token: write
      contents: read
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
      wmill-base-url:         https://windmill-server-cfvpf3ocvq-ey.a.run.app
    # Note: no `secrets:` block. The Windmill CI token lives in GCP Secret
    # Manager (hallotheo-wmill-token) and is fetched at runtime by the deploy
    # SA via WIF — see the One-time per-repo setup section below.
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

### 2. Secret Manager binding (shared Windmill token)

The Windmill CI token lives **once** in GCP Secret Manager as
`hallotheo-wmill-token` (org-shared, created once by an admin). Each new
deploy SA gets read access to that secret:

```bash
gcloud secrets add-iam-policy-binding hallotheo-wmill-token \
  --project=${PROJECT} \
  --member="serviceAccount:${REPO}-deploy@${PROJECT}.iam.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor
```

The deploy workflow reads it at runtime via the SA's WIF identity — there's
no per-repo `gh secret set` needed for org-shared tokens.

(The `/new-app` skill in `builder-tools` runs this binding automatically as
part of WIF setup. It's listed here for manual setup or troubleshooting.)

### 3. One-time org bootstrap (admin only — do once per org)

The shared secret itself needs to exist before any repo can use it. The org
admin runs this once, never again until token rotation:

```bash
# Create the Windmill CI token secret. Get the token value from Windmill's UI
# (Settings → Tokens, label github-actions-ci, scope workspace_owner).
echo -n "<WMILL_TOKEN_VALUE>" | gcloud secrets create hallotheo-wmill-token \
  --project=project-shepherd-494112 \
  --replication-policy=automatic \
  --data-file=-

# Rotations later: add a new version (workflows read --version=latest).
echo -n "<NEW_TOKEN_VALUE>" | gcloud secrets versions add hallotheo-wmill-token \
  --project=project-shepherd-494112 \
  --data-file=-
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
| `wmill-base-url` | required if `app-path` set | E.g. `https://windmill-server-cfvpf3ocvq-ey.a.run.app`. |
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
