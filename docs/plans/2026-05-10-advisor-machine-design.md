---
title: Advisor Machine — design spec
status: draft (v1)
date: 2026-05-10
rig: advisor_machine
bead-prefix: am
---

# Advisor Machine

A Gas Town rig that turns a fuzzy question into a council of independent advisor agents, lets you steer a synthesis loop, and outputs a me-facing memo with calibrated confidence. Every advisor runs in isolated context, no cross-talk. Every council leaves a permanent ledger entry.

The user-facing entry point is `/council`. The rig directory is `advisor_machine` because the council itself is one mode of a broader advisor-machine concept; future rigs (e.g. operator agents that turn memos into action plans) can live in the same repo.

---

## 1. Problem

Hard questions don't fit one model's voice. A single LLM exchange tends to converge on a plausible-sounding answer, hedge, and miss the load-bearing tension. Multi-voice prompting in one context window is worse — the model averages the personas into mush.

Independent advisor agents, each in their own context, attacking the same question from declared angles, then synthesized by a fourth party — that's the shape that produces non-obvious advice. The risk is the system producing the *appearance* of insight (lots of voices, polished memo) without the substance. Guarding against that risk is a first-class design goal, not a polish item.

---

## 2. User experience

From a Mayor session:

```
> /council "I'm thinking about hiring a COO instead of another senior engineer."

[Intake] I have a few questions before I draft the lineup.
[Intake] What's the current size of the team and revenue stage?
> 12 people, $3M ARR, mostly engineers.
[Intake] What problem are you hoping the COO solves that another engineer wouldn't?
> Sales and ops are eating my time and I can't ship.
[Intake] Is this a 12-month bet or a permanent role?
> Permanent if it works.

[Intake] Drafted lineup:
  - Optimist        — the upside case for a COO at this stage
  - Realist         — typical failure modes for early-stage COO hires
  - Pre-mortem      — "you hired a COO and it went badly — what happened?"
  - Researcher      — base rates for COO hires at sub-$5M ARR
  - First-Principles — what is the actual bottleneck and is COO the right shape?
  - ad-hoc: Founder-CEO who has done this — has hired a COO at this stage
Approve, edit, or restart? [y/e/r]
> y

[Mayor] Slinging 6 advisors in parallel... (bead am-001)
[Mayor] All 6 returned. Synthesizing...
[Synth] Round 1 summary ready. Proposed follow-ups:
  - Ask Realist + Founder-CEO: "what's the cheapest test before committing?"
  - Ask Researcher: "any base-rate data on COO tenure < 18mo?"
Run round 2? [y/n/edit]
> y

[Mayor] Round 2 complete. Writing memo...
[Scribe] Memo: 🟡 Sharpened.
         Vault: ~/ADSB/Council/2026-05-10-coo-vs-engineer.md
         Bead:  am-001
```

The Mayor session is the cockpit. Advisors and synth/scribe run as parallel rigs with isolated context.

---

## 3. Architecture

### 3.1 Flow

```
You (Mayor session)
  │  /council "..."
  ▼
Intake (in Mayor's context)        ← conversational, one Q at a time
  │  refines question, drafts lineup
  ▼  [you approve / edit / restart]
Advisors (parallel rigs)            ← isolated context, no sharing
  Library personas + ad-hoc generated personas
  ▼
Synthesizer (rig)                   ← finds the crux, proposes follow-ups
  ▼
Mayor presents to you               ← "approve round 2?" loop
  ▼  (up to N rounds, you gate each)
Scribe (rig)                        ← writes memo + assigns verdict
  ▼
Bead (full audit) + Vault (memo)
```

### 3.2 Components

**Intake** — runs in the Mayor's existing context, no separate rig. Reads the initial dump, asks clarifying questions one at a time until it can articulate: (a) the actual question, (b) the decision or output you need, (c) the constraints, (d) the topic tags. Drafts the advisor lineup with one-line rationales. Has an escape hatch: if clarification stalls (the user's answers aren't sharpening the question), intake stops and recommends either offline refinement or a minimal "scoping council" (Researcher + First-Principles only). The judgment about stalling is intake's to make, not a fixed question-count.

**Advisors** — each is a Gas Town rig slung in parallel. Each sees only: the refined question, the constraints, and its own persona prompt. It cannot see the other advisors' prompts or outputs. Returns a structured markdown file with `Position`, `Key reasoning`, `What would change my view`, `Open questions for the room`.

**Synthesizer** — a single rig that reads all advisor outputs after each round. Its primary deliverable is the **crux**: the single fact, assumption, or value judgment that, if resolved, would settle the question. Secondary: consensus points (real ones, not just absence of disagreement), real disagreements, the strongest single objection, and *proposed* follow-up questions targeted at specific advisors. The synth does not decide to loop — it proposes; the Mayor relays to you for approval.

**Scribe** — a single rig that runs once at the end. Reads everything (refined question, all advisor outputs across all rounds, all synth summaries, your approval notes). Writes the final memo using the template in §5 and assigns a verdict (🟢/🟡/🔴). Forbidden from adding its own opinion, smoothing real disagreement into mush, or recommending actions unless you asked.

### 3.3 Advisor sourcing

Hybrid: a curated library of named personas plus the ability to mint ad-hoc advisors per question.

v1 library:
- **Optimist** — upside case, what makes this work
- **Realist** — base rates, typical outcomes
- **Pre-mortem (Debbie Downer)** — "it failed — narrate why"
- **Expander** — how to make the idea bigger / more exciting
- **Researcher** — fact-injector, not curator (see §6.4)
- **Devil's Advocate** — strongest case against the apparent answer
- **First-Principles** — strip to the actual underlying question
- **Stakeholder-Empathy** — view from the people affected

Ad-hoc advisors: intake can mint custom personas with a one-shot prompt (e.g. "Mortgage industry veteran circa 2008", "Founder-CEO who has hired a COO at this stage"). These are not auto-added to the library — they live only in their council bead. Promotion to the library is a deliberate manual step.

---

## 4. Artifacts

### 4.1 The council bead

One bead per council, prefix `am-`. Files attached:

```
am-NNN/
├── 00-intake.md            # original dump + clarifying Q&A transcript
├── 01-question.md          # refined question, constraints, topic tags
├── 02-lineup.md            # advisor roster + rationale + your edits
├── advisors/
│   ├── round-1/
│   │   ├── optimist.md
│   │   ├── realist.md
│   │   ├── pre-mortem.md
│   │   ├── researcher.md
│   │   ├── first-principles.md
│   │   └── adhoc-founder-ceo.md
│   └── round-2/
│       ├── realist.md
│       ├── researcher.md
│       └── adhoc-founder-ceo.md
├── synth/
│   ├── round-1.md           # consensus, tensions, crux, proposed follow-ups
│   ├── round-1-decision.md  # your approval / edits
│   └── round-2.md
└── 99-memo.md               # final scribe output (also copied to vault)
```

### 4.2 The vault note

Just the polished memo. Path: `~/ADSB/Council/YYYY-MM-DD-<slug>.md`. Frontmatter links back to the bead ID so you can reach the full transcript from the note.

### 4.3 Context isolation property

The Mayor's context never contains the *insides* of an advisor's reasoning — only their finished structured outputs. This keeps the Mayor's context lean across many rounds and prevents the Mayor from leaking one advisor's reasoning into another's prompt.

---

## 5. The memo template

```markdown
---
council: am-NNN
date: 2026-05-10
topic: <slug>
tags: [business, hiring]
rounds: 2
advisors: [optimist, realist, pre-mortem, researcher, first-principles, adhoc:founder-ceo]
verdict: 🟡 sharpened
---

# <Refined question>

## TL;DR
One paragraph. What the council collectively thinks, what's contested,
and the single most important thing for you to weigh.

## Where the council agreed
- Bullet points of genuine consensus.

## Where the council split
### Position A — held by [Optimist, Expander]
Core claim, strongest reasoning, what would change their mind.
### Position B — held by [Realist, Pre-mortem]
Same structure.

## The crux
The single fact, assumption, or value judgment that would settle this question.

## The strongest single objection
The one thing that, if true, breaks the case. Who raised it, why it matters.

## What you'd need to learn next
Open questions the council couldn't resolve. Cheapest ways to learn each.

## Outlier views worth keeping
Anything a single advisor said that the rest dismissed but might matter.

## Researcher's finds (if applicable)
Specific facts that would change a mind, with one-line relevance each.

---
*Full transcript: bead am-NNN*
```

**Voice:** me-facing, plain language, no hedging. The scribe is told: you're writing for a smart busy reader who wants signal, not a balanced essay.

**Verdicts:**
- 🟢 **Resolved** — high-confidence consensus on a non-obvious answer
- 🟡 **Sharpened** — didn't resolve, but surfaced the real tradeoff/crux you didn't have
- 🔴 **Inconclusive** — didn't move you forward; here's why and what to do instead

A 🔴 is honest, not a failure. The failure mode is hiding 🔴 behind a polished memo.

---

## 6. Anti-slop guarantees

The deepest risk: generic wisdom dressed up as advice. These mechanisms are first-class.

### 6.1 Specificity is required

Every advisor persona prompt ends with:
> *Every claim you make must be grounded in a specific detail from the question. If you find yourself writing something that would be true of any business decision, delete it. Generic wisdom is failure.*

### 6.2 Forced commitment

"It depends" is a failure mode. Advisors are told:
> *If you're tempted to hedge, instead pick the most likely scenario, answer for that, then name what would change your answer.*

### 6.3 Synth's job is the crux

The synthesizer's primary deliverable is one sentence: *"What is the single fact, assumption, or value judgment that, if resolved, would settle this question?"* Everything else is supporting material.

### 6.4 Researcher as fact-injector

Researcher's job is not "find interesting reading." It's:
> *Surface only facts that would change someone's mind on this question. Decision-altering evidence — not interesting reading, not background context. If you don't find any, say so plainly; don't pad.*

### 6.5 Forced dissent

If synth judges that the advisors converged suspiciously fast on round 1 — i.e. there's no real tension surfaced — the Mayor automatically slings one extra advisor: the **Strongest Opposing Case**, whose explicit job is to steelman the rejected position. Prevents groupthink theater. The synth makes the judgment call on what "suspiciously fast" means in context; a numeric threshold would be fake precision until we see real distributions. Cost: one extra rig invocation when triggered.

### 6.6 The "so what" gate

Before writing the memo, the scribe must answer in one sentence:
> *If you only read the TL;DR, what would you do differently than before you asked?*

If it can't answer, the memo gets 🔴 and explains why.

### 6.7 Calibrated self-rating

The verdict (§5) is mandatory. 🔴 is not hidden.

### 6.8 You can fire the council

`/council reject "this is all generic"` kills the run, logs why in the bead, and the rejection signal feeds prompt tuning. The ledger remembers which councils produced 🔴 outputs so consistently-weak personas can be retired.

---

## 7. Edge cases & failure modes

| Case | Handling |
|------|----------|
| Advisor rig errors or times out | Retry once. If it fails again, proceed without that advisor — synth and memo explicitly note the absence. No silent dropping. |
| Synth finds no real disagreement | Skip the approval loop, go straight to scribe. Fast path. |
| You change your mind during intake | `/council restart` discards in-progress bead. `/council edit-question` revises after lineup is drafted but before advisors are slung. |
| Cross-advisor contamination | Hard rule: an advisor's prompt never sees another advisor's output. Follow-up rounds inject only *that advisor's own* prior output. |
| Runaway cost | Per-council budget cap (configurable; default tuned from dogfooding, not pre-set). Mayor warns before crossing it. The "you approve each round" loop is the main throttle. |
| Question too vague after intake | If intake's clarifying questions aren't sharpening the question, intake stops and recommends offline refinement or a minimal scoping council (Researcher + First-Principles). Judgment call by intake, not a fixed counter. |
| Vault unavailable / write fails | Memo still lands in bead. Mayor reports vault failure and provides the bead path. |

---

## 8. v1 scope

Build only this. Defer everything else.

- `/council "..."` invocation from Mayor session
- Intake: conversational, one Q at a time, escape hatch when clarification stalls (intake's judgment)
- 8-persona library + ad-hoc persona generation
- Parallel advisor rig sling with structured output format
- Synth rig: crux + consensus + tensions + proposed follow-ups
- Synth-proposes / you-approve loop (you gate every round)
- Forced-dissent advisor when synth judges round 1 produced no real tension
- Scribe rig with verdict (🟢/🟡/🔴) and "so what" gate
- Bead-per-council with full transcript layout (§4.1)
- Vault note with frontmatter back-link
- `/council reject` command

---

## 9. Deferred to v2+

| Feature | Why deferred |
|---------|--------------|
| **Topic context packs** | Vault notes attached to advisor prompts based on detected topic tags (`business`, `family`, etc.). Want to see how v1 performs before adding this complexity. |
| **Operator agent / action plan** | Optional `actions.md` produced by a separate agent that turns the memo into concrete next steps. Kept separate so the council itself stays an advice tool, not a doer. |
| **Auto-promotion of strong ad-hoc personas to library** | Currently a deliberate manual step. Could become automatic with usage data. |
| **Cross-council retrospective** | "Show me all councils on hiring questions and how my decisions played out." Requires outcomes-tracking we don't have yet. |
| **Multi-modal advisors** | Image/document inputs. v1 is text-only. |

---

## 10. Rollout & how we'll know it works

This isn't unit-testable in the normal sense. The question is whether memos earn their keep.

- **Phase 0 — Skeleton:** rig type defined, 8 personas, intake → advisors → synth → scribe pipeline runs end-to-end. No follow-up loop. No forced dissent. Just the pipe.
- **Phase 1 — Dogfood:** run a meaningful sample of real councils on questions Adam actually has. Adam rates each 🟢🟡🔴 independently. Track agreement between his verdict and the scribe's. Stop when patterns emerge, not at a fixed count.
- **Phase 2 — Tune prompts:** every 🔴 gets a postmortem. Persona prompts and intake clarifiers get tightened. Re-run.
- **Phase 3 — Loop + dissent:** turn on synth-proposes / you-approve and the forced-dissent trigger. Measure whether round 2 changes the memo or just adds words.
- **Phase 4 — v2 features:** context packs, operator agent. Only after the core has earned trust.

**Informal success metric:** when Adam has a hard question, does he reach for `/council` instinctively, or does he forget it exists? If he forgets it exists, it's slop.

---

## 11. Open questions

These are intentionally left open for the implementation plan to resolve:

1. **How does intake reach the user mid-flight?** The Mayor is conversational — intake just happens in-context. But during the synth-approval gate, does the Mayor block on user input, or does it post to mail and let the user respond async? v1: block in-context. v2 can consider async.
2. **Round budget default.** No numeric default until Phase 1 produces evidence. v1 enforces only "you approve each round" as the throttle; if that proves insufficient, add a numeric ceiling informed by real cost data.
3. **Persona prompt storage.** Markdown files in the rig repo under `personas/<name>.md`, version-controlled. Library updates are PRs against the rig.
4. **Forced-dissent trigger.** v1 leaves this as a judgment call by the synth ("did round 1 produce real tension?"). If synth proves bad at calling it, replace with a measured threshold informed by real distributions — not a guessed one.

---

## 12. Next steps

1. File bead `am-001` ("Build v1 Advisor Machine") with this design attached.
2. Write implementation plan (`writing-plans` skill) for Phase 0 skeleton.
3. Initialize the rig as a git repo and push to `github.com/adamjdavidson/advisor_machine`.
4. Begin Phase 0 build.
