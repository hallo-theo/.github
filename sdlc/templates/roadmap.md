# Roadmap: <app title>

<!--
Phase 3 · the admin agent's build plan. Written by the decomposer agent right
after the first slice merges (dispatched by the Front Door as
front-door-decompose) and committed as plan/roadmap.md. The roadmap PR rides
the review-then-green policy like every agent PR: theo-pr-reviewer approves,
then it merges itself. "If it cannot express its plan as the artifact, it
does not get workers."

Two files, one truth:
  plan/roadmap.md    — this file, the human-readable plan.
  plan/tickets.json  — the machine-readable twin. The Front Door ingests it
                       on merge to populate the ticket board and start
                       dispatching workers. The two MUST agree; the reviewer
                       treats divergence as a blocking finding.
-->

**Intent:** <!-- intent/<slug>.md — link it; never copy requester text out of
its fence. The PII rules from intent/ apply here too. -->

## Mission

<!-- One paragraph in your own words: the outcome the app must deliver. -->

## Delivered so far

<!-- What the merged first slice already covers. Workers extend it — they do
not rebuild it. -->

## Waves

<!--
Tickets grouped into waves. Tickets in the same wave run in PARALLEL (up to
the platform ceiling), so they must touch DISJOINT areas of the repo — two
workers in one file is a merge conflict, not a plan. Ordering between waves
is carried by blocked_by, never by prose.
-->

| ID | Title | Area | Wave | Blocked by | Acceptance criteria |
|----|-------|------|------|------------|---------------------|

## Out of scope

<!-- What deliberately stays unbuilt, so workers don't wander. -->

## Risks / escalations

<!-- Anything likely to need a human: unclear intent, missing access to a
declared system, domain decisions. Escalate — never self-grant access. -->

---

## `plan/tickets.json` — the contract

Every field is **required** for every ticket — the org learned the hard way
that optional schema fields rot ("the system prompt is only advice"). The
decompose workflow validates the shape before the PR opens and the Front Door
refuses malformed files at ingestion.

```json
[
  {
    "id": "TK-1",
    "title": "short, imperative",
    "description": "enough context for a worker that has read nothing else but AGENTS.md and the intent",
    "acceptance_criteria": ["each entry independently testable"],
    "blocked_by": [],
    "area": "api",
    "wave": 1
  }
]
```

Hard limits, all enforced:

- `id` matches `^TK-[0-9]+$` and is unique in the file.
- `acceptance_criteria` is non-empty; `blocked_by` may be empty but must
  only reference ids that exist in this file.
- A wave-N ticket may only be blocked by tickets in waves < N.
- At most **12 tickets** per roadmap. If the idea needs more, the later work
  belongs to a follow-up roadmap after this one ships.
- `[]` (zero tickets) is valid and means the first slice already delivers
  the intent — say so under Mission.
