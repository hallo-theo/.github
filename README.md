# hallo theo — shared CI/CD definitions

Reusable GitHub Actions workflows and bootstrap scripts that every hallo theo
app can call into. The goal: each app's CI/CD is **10 lines of YAML** at most,
delegating to the workflows defined here.

## What's here

| Path | What it is |
|------|------------|
| `.github/workflows/python-ts-pr.yml` | Reusable PR check — Python (uv, ruff, pyright, pytest) + TS (npm, tsc, vitest). Both sides optional via inputs. |

Coming soon (not yet built):
- `python-ts-deploy.yml` — reusable deploy (Cloud Build + Cloud Run + `wmill app push`)
- `scripts/bootstrap-wif.sh` — interactive Workload Identity Federation setup
- `scripts/bootstrap-windmill-token.sh` — helper for creating the CI Windmill token

## How to adopt in your app

Add this file to your repo at `.github/workflows/pr.yml`:

```yaml
name: PR
on: pull_request

jobs:
  ci:
    uses: hallo-theo/.github/.github/workflows/python-ts-pr.yml@main
    with:
      api-path: api                              # path to your Python backend (omit if none)
      api-package: object-details-api            # uv workspace package name (optional)
      app-path: app/object_details.raw_app       # path to your Vite frontend (omit if none)
    # secrets: inherit                           # uncomment once we add a deploy step that needs them
```

That's it. Push the file, open a PR, the checks appear on the PR page.

### Inputs

| Input | Default | Notes |
|-------|---------|-------|
| `python-version` | `"3.12"` | |
| `node-version`   | `"20"`   | |
| `api-path`       | `""`     | Path to Python source. Empty = skip backend jobs. |
| `api-package`    | `""`     | uv workspace package, used as `uv run --package <name> pytest …`. Optional. |
| `app-path`       | `""`     | Path to the frontend. Empty = skip frontend jobs. |

### Pure-Windmill apps (no FastAPI)

Same workflow, just leave `api-path` unset:

```yaml
jobs:
  ci:
    uses: hallo-theo/.github/.github/workflows/python-ts-pr.yml@main
    with:
      app-path: app/my_app.raw_app
```

The Python job is skipped via a workflow-level `if:`.

## Why a separate repo

GitHub treats this repo (`hallo-theo/.github`) as the org's default-files
repo: PR templates, issue templates, and the org-profile README all live
here. Reusable workflows in `.github/workflows/` aren't org-default magic —
they're regular workflow files that other repos reference via the `uses:`
syntax. Living in the same repo as the org-defaults just keeps everything
shared-and-versioned in one place.

## Versioning

Today: `@main` — adopters point at the moving tip. Move to `@v1` tags once
the workflow is stable enough that breaking changes need a bump signal.
