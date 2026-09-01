# Review policy

<!--
Stage 5 · Deploy. Copy to the REPO ROOT as REVIEW.md.
Defines what the agentic review pass looks for. Versioned, so changes to
review policy are reviewable like any other change.

Findings never approve and never block. The required `gates-passed` check and
the ruleset decide what merges.
-->

## Passes, in severity order

1. **Bugs** — logic errors, unhandled cases, broken invariants, race
   conditions, incorrect error handling.
2. **Security** — injected or interpolated untrusted input, secrets in the
   diff, widened permissions or tool surfaces, authentication or
   authorisation bypass.
3. **Compliance with `spec.md` and `plan.md`** — does the diff deliver what
   the spec said, and does it follow the plan? Flag scope the spec did not
   ask for.

## Important vs Nit

- **Important** — would cause a defect, a security issue, or a spec
  divergence. Always report.
- **Nit** — style, naming, preference. **Cap: 5 per PR.** Beyond the cap,
  drop them; a review of 40 nits does not get read.

## Do not report

- Formatting that the formatter owns (`ruff format`, `prettier`).
- Anything lint or typecheck already catches — that is `gates-passed`' job,
  and duplicating it trains people to skim reviews.
- Missing tests where the repo has no test suite yet. Say it once, in one
  finding, not per file.
- Speculative refactors and "consider extracting". Not a review finding.

## Scope boundary

Review catches **diff-local** defects. Invariants spanning files have **no
diff-local signature** — e.g. two tools added to a registry but not named in
the prompt inventory is a clean diff with the prompt file untouched, and no
reviewer, human or AI, can see it.

**Do not write review instructions for cross-artifact invariants.** They
belong in required CI as contract tests. If a review finding could only have
been found by comparing two files the PR did not both touch, that is a
missing test, not a missing reviewer.

## Repeat findings

A mistake flagged **twice** stops being a review finding and becomes a rule in
`AGENTS.md`. Review is not the place to keep re-teaching the same thing.
