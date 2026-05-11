---
title: Advisor output contract
version: 1
status: active
---

# Advisor Output Contract

Every advisor in a council returns one Markdown document using this structure. The contract is intentionally narrow: it makes independent advisor outputs easy for the synthesizer to compare without letting the advisors drift into polished but generic essays.

## Required inputs

Each advisor receives only:

- The refined question.
- The user's stated constraints and relevant context.
- The advisor's own persona prompt.
- For follow-up rounds only, that advisor's prior output and the follow-up question addressed to that advisor.

Advisors must not assume they have seen any other advisor's reasoning.

## Required behavior

- Take a position. Do not write a balanced essay.
- Every claim you make must be grounded in a specific detail from the question.
- If you find yourself writing something that would be true of any business decision, delete it.
- If you're tempted to hedge, instead pick the most likely scenario, answer for that, then name what would change your answer.
- Prefer concrete tradeoffs, tests, failure modes, and decision criteria over abstract principles.
- Say plainly when the available facts are too thin. Do not pad.

## Required output

Return exactly these top-level sections:

```markdown
## Position
One direct paragraph stating your answer, recommendation, warning, or frame. Commit.

## Key reasoning
- Ground each point in a concrete detail from the question.
- Explain why that detail matters.
- Name the assumption underneath your reasoning when it is doing real work.

## What would change my view
- List the specific fact, observation, constraint change, or user value judgment that would make you revise your position.
- Be concrete enough that the synthesizer can turn this into a follow-up question.

## Open questions for the room
- Ask only questions that another advisor, the user, or lightweight research could plausibly resolve.
- Avoid broad prompts like "what are the risks?" unless you name the exact risk.
```

## Quality bar

A strong advisor output is useful even if the final memo disagrees with it. It should give the synthesizer a clear position, the strongest reasoning for that position, the uncertainty that matters, and questions that move the council toward the crux.

A weak output sounds wise but could be pasted into any similar decision. Generic wisdom is failure.
