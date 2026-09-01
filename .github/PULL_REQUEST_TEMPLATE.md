<!--
Org-wide PR template. GitHub applies this to every hallo-theo repo that does
not define its own, so this file is the one place the SDLC artifact chain is
joined. Delete the rows that do not apply to your repo class (see below).
-->

## Artifacts

<!--
The chain, in the playbook's words: "Every stage commits an artifact the next
stage can read. Together, the intent, the spec, the plan, the diff and the
review findings are the audit trail."

Pin the plan at its approved blob SHA (`git rev-parse HEAD:plan/<slug>.md`).
Without the SHA, a "does the diff match the plan?" check compares the diff
against a plan that may have been rewritten in the same commit to match it —
which passes trivially, forever.
-->

| Stage | Artifact | This PR |
|-------|----------|---------|
| 1 · Plan | `intent.md` | <!-- intent/<slug>.md or Notion URL --> |
| 2 · Design | `spec.md` | <!-- spec/<slug>.md --> |
| 3 · Build | `plan.md` | <!-- plan/<slug>.md @ <blob-sha> --> |

**Required by repo class** — `script`: none of the above, a one-line summary is
enough. `application`: spec + plan for anything that is not a fix or a bump.
`acting-agent`: all three, plus the behaviour-bearing paths below.
`platform`: the `terraform plan` output posted below *is* the plan artifact.

## What changed and why

<!-- One paragraph. What a reviewer needs to know that the diff does not say. -->

## Verification

<!--
Stage 4. Paste the actual output of `make verify` — not "tests pass".
The claim is not that you ran it; the claim is what it printed.
-->

```
$ make verify

```

## Behaviour-bearing paths touched

<!--
acting-agent repos only. Tick any that this PR changes. A change here is a
BEHAVIOUR change even when the diff looks like a refactor, and it needs a
golden-set run — not just a green gate.
-->

- [ ] prompts / prompt fragments
- [ ] tool or function definitions exposed to a model
- [ ] confidence thresholds, scoring, or gating logic
- [ ] model or model version
- [ ] none of the above

## Irreversible side effects

<!--
Does this PR change anything that writes to a system we cannot un-write?
Impower postings, payments, outbound email, `wmill sync push`, BigQuery
truncate, HubSpot writes, d.velop uploads. If yes, name the file and say what
gates it before the write commits.
-->

- [ ] No irreversible side effect is added or changed by this PR
- [ ] Yes — described above, with its pre-write gate named

---

<!--
Collapsed-roles rule: on a 1–2 person team the author is often also the
product owner and the approver. Do not simulate handoffs. If that is the case
here, say so plainly and list the machine gates standing in for the missing
independence:

  author = PO = approver; independent controls: gates-passed, contract tests,
  golden reconciliation

Mitigations (rollback, re-tag, quarantine, disable) do NOT require the
artifact chain. Ship the fix, link the replay, and open the corrective PR
afterwards.
-->
