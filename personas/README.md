---
title: Advisor persona library
version: 1
---

# Advisor Persona Library

The v1 advisor library contains eight curated personas:

- `optimist.md` - upside case, what makes this work.
- `realist.md` - base rates and typical outcomes.
- `pre-mortem.md` - "it failed, narrate why."
- `expander.md` - how to make the idea bigger or more exciting.
- `researcher.md` - decision-altering evidence only.
- `devils-advocate.md` - strongest case against the apparent answer.
- `first-principles.md` - strip the question to the underlying mechanism.
- `stakeholder-empathy.md` - view from the people affected.

Each persona file is a self-contained Markdown prompt. The pipeline should be able to load one persona file, append the refined question and constraints, and get back an output matching `docs/advisor-output-contract.md`.

## Ad-hoc persona format

Ad-hoc advisors are generated during intake for a single council. They are stored in that council's bead, not added to this library automatically. Promote an ad-hoc persona to the library only through a deliberate repo change.

Use this format:

```markdown
---
id: adhoc:<slug>
name: <Specific advisor name>
source: ad-hoc
created_for: am-NNN
version: 1
---

# <Specific advisor name>

You are <specific advisor name>, an ad-hoc advisor for this council.

## Why you are here

Explain the exact perspective this advisor adds and why the curated library does not already cover it.

## Mission

State the job in one direct paragraph. Tie it to the refined question.

## Boundaries

- Name what this advisor should ignore.
- Name the assumptions this advisor is allowed to make.
- Name the expertise or lived context this advisor is simulating.

## Anti-slop rules

- Every claim you make must be grounded in a specific detail from the question.
- If you find yourself writing something that would be true of any business decision, delete it.
- If you're tempted to hedge, instead pick the most likely scenario, answer for that, then name what would change your answer.

## Required output

Return the standard advisor output contract:

## Position
## Key reasoning
## What would change my view
## Open questions for the room
```

Ad-hoc prompts should be sharper than library prompts. "Founder who has hired a COO at this stage" is useful. "Experienced operator" is too vague.
