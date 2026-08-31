# Plan: <short title>

<!--
Stage 3 · Build. Commit to plan/<slug>.md, then pin its blob SHA in the PR:
    git rev-parse HEAD:plan/<slug>.md
Produced in plan mode (read-only) and iterated before any code is written.
-->

**Spec:** <!-- spec/<slug>.md -->

## Files that change

<!-- Actual paths. If you cannot list them, the plan is not ready. -->

## Order of work

<!-- Numbered. Each step independently reviewable where possible. -->

## Tests that prove it

<!-- Which test, asserting what. For a bug: the failing test comes first. -->

## Risks

<!--
Interrogate the plan before accepting it: what could break? which is the
riskiest step? what does this touch that is shared with another repo or
another session?

Name any shared mutable runtime this work touches — the Windmill dev
workspace, a shared database, a fixed staging slot. Two sessions pushing to
the same Windmill workspace is documented data loss, not a theoretical risk.
-->

## Departures from this plan

<!-- Append here if implementation diverges, in the same commit as the
divergence. The pinned SHA makes edits visible as a revision rather than a
silent retrofit — that is the point, so do not rewrite history above. -->
