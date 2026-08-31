# Spec: <short title>

<!--
Stage 2 · Design. Commit to spec/<slug>.md.
Requirements and design collapse into one session. Attach the intent and the
org policy skills (builder-tools), then ask for a spec that flags its own
concerns.

Same PII rule as intent.md.
-->

**Intent:** <!-- intent/<slug>.md -->

## What changes

<!-- The behaviour that will differ. Written so a reviewer can tell whether
the diff delivered it. -->

## How it will be verified

<!-- REQUIRED. A spec without this is not done. Name the tests, the golden
set, the manual check. "Tests pass" is not verification; say what would have
to be true. -->

## Out of scope

<!-- What this deliberately does not do, so scope creep is visible in review. -->

## Concerns and contradictions

<!--
The playbook's ask, verbatim: "Describe clearly any areas of concern,
especially where you cannot satisfy contradicting policies."

List them. Each one gets worked with the policy owner BEFORE engineering sees
this spec. An empty section here on a non-trivial change usually means the
question was not asked.
-->

## Irreversible side effects

<!-- Does this cause anything we cannot un-do? ERP posting, payment, outbound
email, wmill sync push, BigQuery truncate, DMS upload. If yes: what
deterministic gate sits in front of it, before it commits? -->

## Go / no-go

<!-- Product owner decision, dated. For higher-risk work, consult the tech
lead first. -->
