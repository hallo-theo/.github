# The hallo theo AI-Native SDLC — six stages, one artifact each

Stage names and artifact names are taken **verbatim** from Anthropic's
[AI-Native SDLC Playbook](https://claude.com/blog/the-ai-native-sdlc-playbook).
We do not rename them. We tell ourselves this standard is *benchmarked against
the playbook with documented deviations* — that claim is only auditable if
someone can read both documents and diff them. Renaming stages for style hides
real deviations and invents fake ones.

> "Every stage commits an artifact the next stage can read. Together, the
> intent, the spec, the plan, the diff and the review findings are the audit
> trail."

## The chain

```
intent.md  ──▶  spec.md  ──▶  plan.md  ──▶  diff + tests  ──▶  review findings  ──▶  incident record
 Stage 1        Stage 2        Stage 3         Stage 3/5           Stage 5              Stage 6
   Plan          Design         Build            Test              Deploy              Maintain
                                                                                          │
                                                        new intent.md ◀────────────────────┘
```

| Stage | Artifact | Lives at | Written by | Read by |
|-------|----------|----------|------------|---------|
| **1 · Plan** | `intent.md` | `intent/<slug>.md` | the originator — **explicitly including non-engineers** | Stage 2 |
| **2 · Design** | `spec.md` | `spec/<slug>.md` | pitch owner + agent, with org policy skills attached | Stage 3, and the reviewer |
| **3 · Build** | `plan.md`, then the diff | `plan/<slug>.md`, then the PR | plan mode, then the build session | Stage 4/5 |
| **4 · Test** | the feedback loop | one `make verify` + the eval suite | the repo | agent and human, every iteration |
| **5 · Deploy** | review findings | PR comments, governed by `REVIEW.md` | the agentic review pass | the author; the audit trail |
| **6 · Maintain** | incident record | `lessons.md`, `docs/postmortems/<slug>.md` | whoever ran the incident | the next session; the next eval |

**Artifacts live in the repo the change lands in**, not in a central docs repo.
A central store drifts from the code within a cycle and cannot be reviewed in
the same PR as the change it describes.

**The PR body is what joins them.** See the org-wide
[`PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md). No database,
no new service — the one place all six stages meet is a text field a check can
read.

## Stage 1 · Plan → `intent.md`

Ideas bypass backlog refinement. The originator describes the problem to Claude
in plain language; Claude writes `intent.md` from the org template; the
originator corrects it; it is committed.

Contains: **problem · proposed outcome · affected users and systems ·
constraints · open questions.**

Governance: the intent is accepted or rejected as a logged event (a merged or
closed PR).

**Who accepts, at hallo theo:** we have no product owners — we run Shape Up,
and pitches come from the Product VP. Where the playbook says "product owner",
read **the pitch owner**: the Product VP, or whoever the VP delegates
acceptance to for small internal tools. The control is the *logged acceptance
event*, not the job title. Acceptance is an **event**, not a status — for intents authored in Notion
(where our PMs and PAs work) acceptance exports the page to markdown and
commits it, so Stages 2 and 3 cannot be built on a document that later changed
silently.

⚠️ **PII gate.** Ops staff write intents the way ops staff write: tenant name,
address, IBAN, pasted from Impower. `intent/` and `spec/` are covered by a
deterministic PII check because git history is immutable and replicated into
every clone and every agent session. This is GDPR-load-bearing, not hygiene.

## Stage 2 · Design → `spec.md`

Requirements and design collapse into one session. The pitch owner (or the
engineer taking the pitch) opens a session with the org's policy skills
attached (`builder-tools`) and asks for a spec that **flags its own concerns** — in the playbook's phrasing: *"Describe
clearly any areas of concern, especially where you cannot satisfy contradicting
policies."*

Flagged concerns get worked with policy owners **before engineering sees the
spec.** Then go / no-go.

A spec that does not say **how the change will be verified** is not done.

## Stage 3 · Build → `plan.md`, then the diff

Start in plan mode, read-only. Iterate the plan until it names: **files that
change · order of work · tests that prove it · risks.** Interrogate it — *what
could break? what is the riskiest step?* Then commit the approved plan and
implement.

**Pin the plan's blob SHA in the PR body at approval.** If the implementation
departs from the plan, the plan is updated — and the pinned SHA makes that show
up as a visible revision instead of a silent retrofit. Without the pin, any
"diff matches plan?" check compares the diff against a plan rewritten to match
it, and passes trivially forever.

## Stage 4 · Test → the feedback loop

**One command.** `make verify` runs lint, typecheck and tests. If an agent needs
four different entry points to know whether its work is correct, it will guess.

- Bugs start with a **failing test** that reproduces them, before the fix.
- Paste the **actual output** of `make verify` into the PR. The claim is not
  that you ran it; the claim is what it printed.
- Evals **accrete one per incident**, starting from zero. No 50-task suite up
  front and no monthly tuning ritual — we do not have the headcount, and the
  playbook's own line about adding an eval per incident is a better bootstrap.
- **Agentic evals run nightly and are trend-reported, never a merge gate.**
  30 stochastic tasks at ~0.95 each fail a healthy config ~6–7% of the time,
  and a flaky blocking check gets bypassed, then ignored.

## Stage 5 · Deploy → review findings

`REVIEW.md` at the repo root defines the review passes, ranked by severity:
**bugs · security · compliance against `spec.md` and `plan.md`.** Important vs
Nit, a nit cap of 5, and a do-not-report list.

**Findings never approve or block — the ruleset does.** The single required
check is `gates-passed`. Deploy by **promoting the artifact that already passed
on its PR**: authorisation becomes verifiable provenance rather than a
self-set variable.

Scope boundary that matters: PR review catches **diff-local** defects. Invariants
that span files have no diff-local signature — two tools added to a registry
but not named in the prompt inventory is a syntactically clean diff with the
prompt file untouched, and no reviewer, human or AI, can see it. **Cross-artifact
invariants must be machine-checked contract tests in required CI**, not review
instructions.

## Stage 6 · Maintain → incident record → a new `intent.md`

A deterministic, version-controlled, unit-tested detection script — **no model**
— watches one stable metric against a rolling baseline. Tiers in `bands.yaml`:
1σ log only; 2σ diagnose read-only; 3σ may act via PR or a pre-approved runbook.

The diagnosis is **written as an `intent.md`** and re-enters the pipeline like
anything else. The service owner always triages: fix now / schedule / dismiss —
and a dismissal tunes the bands. When the fix ships, it brings an eval.

Our amendments, because the playbook assumes conditions we do not have:

- **Volume floor.** Sigma bands need ~30+ samples per rolling window. The
  booking job runs ~11×/day, where one failure swings the daily rate ~9 points
  — so bands would either alert-storm or never fire. Below the floor, use
  per-run deterministic contracts where a single violation is the trigger. *A
  control band on a nightly job is an assertion, not a band.*
- **Migration-aware rollback.** Stamp each release with `contains_migration`
  (diff `alembic/versions/` between tags). If set, 3σ auto-act is demoted to
  propose-only: re-tagging an image rolls back code, not schema.
- **Evidence contract.** No tier fires on temporal correlation alone. An
  innocent deploy at 09:00 and third-party throttling at 09:20 satisfies
  "anomaly + recent deployment" — and reverts the wrong thing.
- **The human-executable floor.** Every play with production authority names a
  no-LLM degraded path, and that path is exercised. Our LLM calls route through
  one gateway; an outage there is simultaneously the incident *and* the thing
  that disables the responder.

## What we deliberately do not adopt

| Not adopting | Why |
|---|---|
| Dev-session transcript forwarding | Runtime traces already answer the audit and escrow question; transcripts add GDPR exposure for no gain |
| Managed settings / MDM tier | No MDM; the playbook scopes it to regulated enterprise and calls its example a starting point |
| A 20–50-task agentic eval suite as a merge check | Stochastically flaky as a blocking gate — nightly and trend-reported instead |
| Monthly review-tuning rituals | No headcount; replaced by event-driven accretion |
| Raw `strict` without a merge queue, at high commit rates | N² CI and rebase churn — add the queue first |

## Where we extend the playbook

Four concepts it has no word for, because it assumes one kind of repo and its
governance ends at merge:

1. **Repo classes** — `script` · `application` · `acting-agent` · `platform`.
   The class is not how important the repo is; it is **what can go wrong that a
   code review cannot catch.** It decides which artifacts are required and
   which checks are worth paying for.
2. **Acting agent** — a repo where model output causes an irreversible
   real-world action without a human reading it first. An LLM in the request
   path does *not* qualify if its output terminates in something a human reads.
3. **Run ledger**, beside the deploy ledger. DORA describes the code artifact.
   Rare successful deploys give CFR ≈ 0% while a defect can sit in 44% of
   production runs for a month. Agent products report flag rate by tier,
   tool-call coverage vs inventory, and golden divergence per deploy window.
4. **Reversibility fork** — before exposing any write tool, classify it.
   Reversible (deploys, flags): the playbook stands. Irreversible (ERP
   postings, payments, email): capability-scoped **enforced by test**, a
   deterministic per-decision gate before the side effect commits, a mandatory
   trace — and never an auto-rollback runbook. There is no staging Impower; it
   is a third party's production system.

**All gate and review metrics are reported, never targeted.** First-pass CI
success rises by slicing PRs thinner; falling review time is indistinguishable
from rubber-stamping. Targets attach only to adversarially-measured outcomes —
escaped defects and incidents.
