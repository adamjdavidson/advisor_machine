# Advisor Machine v1 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship the v1 Advisor Machine — a `/council` command that turns a fuzzy question into a council of independent advisor agents, gathers their views, lets the user steer a synthesis loop, and outputs a calibrated memo. Per design spec `2026-05-10-advisor-machine-design.md` (committed `1a6844d`), tracked as bead `am-qvl`.

**Architecture:** Gas Town rig. `/council` slash command runs intake in the Mayor's context. Each advisor is a separate polecat slung via `gt sling`, isolated context, no cross-talk. Synthesizer and scribe are separate polecats too. Bead-per-council collects all artifacts. Final memo lands in bead + vault.

**Tech Stack:**
- **Slash commands**: Markdown with YAML frontmatter at `.claude/commands/*.md` (body becomes prompt)
- **Molecules**: TOML formulas at `/Users/adamdavidson/gt/.beads/formulas/*.formula.toml` (DAG-ordered steps)
- **Dispatch**: `gt sling <bead> <rig>/<role>` (isolated polecat per advisor)
- **Data plane**: `bd` for beads + file attachments (`--append-notes`)
- **Personas**: Markdown files in `advisor_machine/advisors/personas/`
- **Verification**: Each task ends with a manual smoke-test command. Full pipeline test is "run a real council and verify artifacts."

**Reference patterns to model:**
- `mol-deacon-patrol` — long-running watchdog with stepwise execution
- `mol-convoy-feed` — parallel sling-to-polecats from a queue
- `mol-polecat-work` — full polecat lifecycle (load context → work → done)

**Phasing:**
- **Phase 0 — Skeleton:** End-to-end pipe with one advisor, then expand to library. No follow-up loop, no forced dissent. (Tasks 1–11)
- **Phase 1 — Loop + Polish:** Synth-approve loop, forced dissent, verdict logic. (Tasks 12–15)
- **Phase 2 — Dogfood + Tune:** Run real councils, iterate on prompts. (Not coded — operational.)

**Working tree:** All edits happen in `/Users/adamdavidson/gt/advisor_machine/crew/adamd/`. Slash command lives in `/Users/adamdavidson/gt/mayor/` (the Mayor's commands dir, not the rig). Formula files live in `/Users/adamdavidson/gt/.beads/formulas/` (town-level).

**Commit cadence:** Every task ends with a commit. Push after each phase.

---

## Phase 0 — Skeleton

### Task 1: Persona file format and one starter persona

**Why first:** Personas are the simplest concrete artifact. Establishing the format makes the rest of the work obvious.

**Files:**
- Create: `advisors/personas/optimist.md`
- Create: `advisors/personas/README.md` (format documentation)

**Step 1: Write `advisors/personas/README.md`**

```markdown
# Persona Files

Each `.md` file in this directory is one advisor persona. The file content
is loaded verbatim as the system prompt when a polecat is slung as that advisor.

## Format

```
---
name: <persona-slug>
display: <Human-readable name>
description: <one-line what this advisor brings>
---

You are <role>.

<persona-specific guidance>

## Hard rules (do not violate)

- Every claim you make must be grounded in a specific detail from the question.
  If you find yourself writing something that would be true of any business
  decision, delete it. Generic wisdom is failure.
- "It depends" is a failure mode. If you're tempted to hedge, pick the most
  likely scenario, answer for that, then name what would change your answer.
- You cannot see other advisors. Don't reference them.

## Output format

Return a markdown file with these sections, in this order:

### Position
<one paragraph — what you actually think>

### Key reasoning
<3-5 bullets, each grounded in a specific from the question>

### What would change my view
<the specific evidence or argument that would flip you>

### Open questions for the room
<questions you'd want the rest of the council to address>
```

Personas may NOT add additional sections. The scribe relies on this format.
```

**Step 2: Write `advisors/personas/optimist.md`**

```markdown
---
name: optimist
display: The Optimist
description: The upside case — what makes this work
---

You are the Optimist on a council of independent advisors.

Your job is to make the strongest possible case for the upside of the
proposal. You are not a cheerleader. You are an experienced operator who
has seen plays like this work and can articulate *why* — what the specific
mechanisms are, what conditions need to hold, who has done it before and won.

You are paired (silently — you cannot see them) with realists and
pre-mortems. Their job is to find what kills this. Your job is to find
what makes it sing. If you accidentally produce a balanced "here are the
pros and cons" memo, you've failed.

Cite specifics. Name analogues. Identify the exact upside ceiling and what
it takes to reach it.

## Hard rules (do not violate)

- Every claim you make must be grounded in a specific detail from the question.
  If you find yourself writing something that would be true of any business
  decision, delete it. Generic wisdom is failure.
- "It depends" is a failure mode. If you're tempted to hedge, pick the most
  likely scenario, answer for that, then name what would change your answer.
- You cannot see other advisors. Don't reference them.

## Output format

Return a markdown file with these sections, in this order:

### Position
<one paragraph — what you actually think>

### Key reasoning
<3-5 bullets, each grounded in a specific from the question>

### What would change my view
<the specific evidence or argument that would flip you>

### Open questions for the room
<questions you'd want the rest of the council to address>
```

**Step 3: Verify file contents render correctly**

Run:
```bash
ls -la /Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/
cat /Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/optimist.md | head -10
```

Expected: both files exist, optimist.md has frontmatter and the hard-rules section.

**Step 4: Commit**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git add advisors/personas/README.md advisors/personas/optimist.md
git commit -m "Add persona file format and Optimist starter persona

First of 8 personas for v1. Format includes hard rules (no generic
wisdom, no hedging) and a required output schema the scribe depends on."
```

---

### Task 2: Council slash command (intake skeleton)

**Why:** This is the user-facing entry point. Even before advisors work, the slash command should accept input, refine the question conversationally, and produce a `01-question.md` artifact. Wires the front of the pipe.

**Files:**
- Create: `/Users/adamdavidson/gt/mayor/.claude/commands/council.md`

**Step 1: Read 2 existing slash commands as reference**

Run:
```bash
cat /Users/adamdavidson/gt/mayor/.claude/commands/done.md
cat /Users/adamdavidson/gt/mayor/.claude/commands/handoff.md
```

Note: YAML frontmatter (description, allowed-tools, argument-hint), then markdown body that becomes the system prompt. `$ARGUMENTS` is the user's input.

**Step 2: Write `council.md`**

```markdown
---
description: Convene a council of independent advisor agents on a question
allowed-tools: Bash(bd create:*), Bash(bd update:*), Bash(bd show:*), Bash(gt sling:*), Bash(gt mail send:*), Read, Write, Edit
argument-hint: "<your question or problem>"
---

# /council

You are conducting the intake phase of an Advisor Machine council on behalf of the user.

## The user's question (raw)

$ARGUMENTS

## Your job in this phase

1. Read the question. If it's specific enough to act on, skip to step 3.
2. Otherwise, ask **one clarifying question at a time** until you can articulate:
   - The actual question (what they want answered)
   - The decision or output they need (a yes/no? a recommendation? a framing?)
   - The constraints (budget, timeline, irreversibility, who else is affected)
   - Topic tags (e.g., `business`, `hiring`, `family`, `writing`)
3. **Escape hatch:** if your clarifying questions aren't sharpening the question (the user keeps adding context but the decision isn't crystallizing), stop and recommend either offline refinement or a minimal "scoping council" (Researcher + First-Principles only). Don't force the full council on a poorly-formed question.
4. Once you have the refined question, **draft an advisor lineup** from the persona library at `/Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/`. Pick the personas that fit the question, and propose ad-hoc personas where the library doesn't cover a needed angle.
5. Present the lineup to the user with one-line rationales. Wait for approval, edits, or restart.

## After approval (Phase 0 skeleton — single advisor)

For Phase 0, you will dispatch ONE advisor to validate the pipeline. Multi-advisor parallel dispatch comes in Task 7.

Run:
```bash
COUNCIL_BEAD=$(bd create "Council: <slug>" \
  --type task \
  --description "Refined question, lineup, raw intake transcript" \
  --labels "council,phase-0" \
  | grep -oE "am-[a-z0-9]+")
echo "Council bead: $COUNCIL_BEAD"
```

Write the artifacts to the bead via `bd update --append-notes` after each phase.

## Hard rules

- One question at a time during intake.
- Never invent constraints the user didn't state.
- Never proceed to advisor dispatch without explicit user approval of the lineup.
- The final memo is written by the scribe agent, not by you.
```

**Step 3: Smoke-test the command exists and parses**

Run:
```bash
ls -la /Users/adamdavidson/gt/mayor/.claude/commands/council.md
head -10 /Users/adamdavidson/gt/mayor/.claude/commands/council.md
```

Expected: file exists, frontmatter parses (description, allowed-tools, argument-hint fields visible).

**Step 4: Live smoke test (manual)**

In a Mayor Claude Code session, type `/council "Should I rename the project?"` — verify Claude loads the command and starts asking clarifying questions one at a time. **Do not yet expect advisor dispatch to work.** Quit after the lineup-approval prompt.

**Step 5: Commit**

```bash
cd /Users/adamdavidson/gt/mayor
git add .claude/commands/council.md 2>/dev/null || true  # mayor/ may not be a git tree; if so skip
# If mayor/ is not a git working tree, the slash command lives in the Mayor's
# local Claude config rather than the rig repo. Note in commit message of next
# rig-repo commit that this was created.
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git commit --allow-empty -m "Add /council slash command at Mayor level (Phase 0 intake)

Slash command lives at /Users/adamdavidson/gt/mayor/.claude/commands/council.md
(outside the rig repo, in the Mayor's local Claude config). Drives intake
conversation and lineup approval. Advisor dispatch is stubbed; wired in T7."
```

---

### Task 3: Bead artifact layout helpers

**Why:** Every step writes structured files into the council bead. Centralize the layout so individual steps don't reinvent paths.

**Files:**
- Create: `scripts/council-bead.sh`

**Step 1: Write the helper script**

```bash
#!/usr/bin/env bash
# Helpers for the council bead artifact layout.
# Source this from formula steps and the slash command.
#
# Usage:
#   COUNCIL_BEAD=am-qvl
#   COUNCIL_DIR=$(council_dir "$COUNCIL_BEAD")
#   write_intake "$COUNCIL_BEAD" "raw intake markdown"
#   write_question "$COUNCIL_BEAD" "refined question markdown"

set -euo pipefail

# Per-council scratch directory under .runtime/
council_dir() {
  local bead="$1"
  local dir="/Users/adamdavidson/gt/advisor_machine/.runtime/councils/$bead"
  mkdir -p "$dir/advisors/round-1" "$dir/synth"
  echo "$dir"
}

# Write an intake transcript and attach to bead
write_intake() {
  local bead="$1" content="$2"
  local dir
  dir=$(council_dir "$bead")
  printf '%s\n' "$content" > "$dir/00-intake.md"
  bd update "$bead" --append-notes "## 00-intake.md attached
$content"
}

write_question() {
  local bead="$1" content="$2"
  local dir
  dir=$(council_dir "$bead")
  printf '%s\n' "$content" > "$dir/01-question.md"
  bd update "$bead" --append-notes "## 01-question.md attached
$content"
}

write_lineup() {
  local bead="$1" content="$2"
  local dir
  dir=$(council_dir "$bead")
  printf '%s\n' "$content" > "$dir/02-lineup.md"
  bd update "$bead" --append-notes "## 02-lineup.md attached
$content"
}

write_advisor() {
  local bead="$1" persona="$2" round="$3" content="$4"
  local dir
  dir=$(council_dir "$bead")
  mkdir -p "$dir/advisors/round-$round"
  printf '%s\n' "$content" > "$dir/advisors/round-$round/$persona.md"
  bd update "$bead" --append-notes "## advisors/round-$round/$persona.md attached
$content"
}
```

**Step 2: Make executable, verify**

Run:
```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
mkdir -p scripts
chmod +x scripts/council-bead.sh
bash -n scripts/council-bead.sh && echo "syntax OK"
```

Expected: `syntax OK`.

**Step 3: Functional test — write a fake intake**

```bash
source ./scripts/council-bead.sh
TEST_BEAD="am-test-$(date +%s)"
mkdir -p /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD
council_dir $TEST_BEAD  # should print the dir
echo "test passed"
rm -rf /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD
```

Expected: prints the dir path, exits 0, cleans up.

**Step 4: Add `.runtime/` to gitignore**

Run:
```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
grep -q "^\.runtime/$" .gitignore 2>/dev/null || echo ".runtime/" >> .gitignore
```

**Step 5: Commit**

```bash
git add scripts/council-bead.sh .gitignore
git commit -m "Add council-bead.sh helpers for artifact layout

Encapsulates the bead-attached file structure (00-intake.md, 01-question.md,
advisors/round-N/*.md, etc.) so formula steps and the slash command don't
reinvent paths. .runtime/ is gitignored — councils are stored in bead/Dolt,
not committed."
```

---

### Task 4: Single advisor formula (mol-advisor-run)

**Why:** Smallest unit of advisor work — given a persona file and a question, produce an advisor output file. Validates that a polecat can be slung, can read inputs, and can write back to its bead.

**Files:**
- Create: `/Users/adamdavidson/gt/.beads/formulas/mol-advisor-run.formula.toml`

**Step 1: Read a reference formula**

Run:
```bash
ls /Users/adamdavidson/gt/.beads/formulas/ | head -10
cat /Users/adamdavidson/gt/.beads/formulas/mol-dog-doctor.formula.toml 2>/dev/null || \
  cat /Users/adamdavidson/gt/.beads/formulas/mol-deacon-patrol.formula.toml | head -60
```

Note: TOML structure (description, formula name, vars, steps with id/title/needs/description).

**Step 2: Write `mol-advisor-run.formula.toml`**

```toml
description = "Run one advisor on a council question and write their output to the council bead"
formula = "mol-advisor-run"
version = 1

[vars]

[vars.council_bead]
description = "The parent council bead ID (e.g., am-qvl)"
required = true

[vars.persona]
description = "Persona slug (e.g., 'optimist', 'realist'). Must match a file in advisors/personas/."
required = true

[vars.round]
description = "Round number (1 for first round, 2+ for follow-ups)"
default = "1"

[[steps]]
id = "load-context"
title = "Load persona and question"
description = """
Read the persona file and the refined question from the council bead.

```bash
PERSONA_FILE=/Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/{{persona}}.md
QUESTION_FILE=/Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/01-question.md

test -f "$PERSONA_FILE" || { echo "Persona not found: $PERSONA_FILE"; exit 1; }
test -f "$QUESTION_FILE" || { echo "Question not found: $QUESTION_FILE"; exit 1; }
```

Read both files into your context. The persona file IS your system identity.
Adopt it. Do not break character to acknowledge the framing.
"""

[[steps]]
id = "respond"
title = "Produce advisor output"
needs = ["load-context"]
description = """
Following the persona's instructions and the required output format
(Position / Key reasoning / What would change my view / Open questions
for the room), write your response.

Output ONLY the markdown — no preamble, no meta-commentary.
"""

[[steps]]
id = "attach"
title = "Write output to the council bead"
needs = ["respond"]
description = """
Save your output to the bead's artifact dir and attach via bd notes.

```bash
source /Users/adamdavidson/gt/advisor_machine/crew/adamd/scripts/council-bead.sh
write_advisor "{{council_bead}}" "{{persona}}" "{{round}}" "$(cat your-response.md)"
```

Then signal completion. The Mayor (or witness) is watching for your output.
"""
```

**Step 3: Verify formula loads**

Run:
```bash
gt formula show mol-advisor-run 2>&1 | head -20
```

Expected: formula description and steps print. If `gt formula show` doesn't exist, try `gt formulas | grep mol-advisor-run`.

**Step 4: Commit**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
# The formula file lives at town level (/Users/adamdavidson/gt/.beads/formulas/),
# which is in the town's git repo, not the rig's. Commit there.
cd /Users/adamdavidson/gt
git add .beads/formulas/mol-advisor-run.formula.toml
git commit -m "Add mol-advisor-run formula

Single-advisor execution: load persona + question, respond, attach output
to council bead. Used by /council to dispatch each advisor in isolated
polecat context."
```

---

### Task 5: End-to-end smoke test with one advisor

**Why:** Before adding more personas or parallel dispatch, prove the full one-advisor path works: intake → bead created → advisor slung → output attached.

**Files:** (no new files — runtime test)

**Step 1: Create a test council bead manually**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
TEST_BEAD=$(bd create "Test Council: Phase 0 smoke" \
  --type task \
  --description "Smoke test for single-advisor pipeline" \
  --labels "council,test,phase-0" \
  | grep -oE "am-[a-z0-9]+")
echo "TEST_BEAD=$TEST_BEAD"
```

**Step 2: Write a fake refined question**

```bash
source ./scripts/council-bead.sh
write_question "$TEST_BEAD" "## Refined question

Should I rename the 'advisor_machine' rig to 'council'?

## Constraints
- Renames cost 30 min plus chasing stale references.
- The user-facing command is already named /council; rig name visible only internally.

## Topic tags
[meta, naming]"
```

Verify: `cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/01-question.md`

**Step 3: Sling the Optimist**

```bash
gt sling "$TEST_BEAD" advisor_machine/polecats \
  --formula mol-advisor-run \
  --vars "council_bead=$TEST_BEAD,persona=optimist,round=1"
```

If the exact sling syntax for passing vars differs from the above, inspect `gt sling --help` and adjust. The principle: dispatch a polecat that will execute `mol-advisor-run` with the given vars.

**Step 4: Wait for completion and verify**

```bash
# Watch for the advisor output file to appear:
until [ -f /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/advisors/round-1/optimist.md ]; do
  sleep 5
  echo "waiting..."
done
echo "DONE"
cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/advisors/round-1/optimist.md
```

Expected: the Optimist's response in the required format (Position / Key reasoning / What would change my view / Open questions for the room).

**Step 5: Inspect the bead**

```bash
bd show $TEST_BEAD
```

Expected: notes include the optimist's full output as an appended section.

**Step 6: Manual review checklist**

- [ ] Output has all four required sections
- [ ] Position is a real opinion (not "it depends")
- [ ] At least one bullet in Key reasoning references a specific from the question
- [ ] The Optimist did NOT add sections beyond the required four
- [ ] The Optimist did NOT reference other advisors

If any fail, the persona prompt needs tightening — return to Task 1 and adjust `optimist.md`.

**Step 7: Commit (no code changes, but record the validation)**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git commit --allow-empty -m "Validate Phase 0 single-advisor pipeline (smoke test passed)

Test bead: $TEST_BEAD
Optimist produced compliant output in required format. Bead artifacts
correctly written to .runtime/councils/.../ and attached via bd notes."
```

---

### Task 6: Remaining 7 personas

**Why:** Once one persona works end-to-end, the rest are mechanical. Each is one file.

**Files:**
- Create: `advisors/personas/realist.md`
- Create: `advisors/personas/pre-mortem.md`
- Create: `advisors/personas/expander.md`
- Create: `advisors/personas/researcher.md`
- Create: `advisors/personas/devils-advocate.md`
- Create: `advisors/personas/first-principles.md`
- Create: `advisors/personas/stakeholder-empathy.md`

**Step 1: For each persona, copy the structure of `optimist.md` and replace the persona-specific content.**

Each persona should keep:
- The frontmatter (name/display/description)
- The "## Hard rules" section unchanged
- The "## Output format" section unchanged

Each persona should customize:
- The opening role statement
- The persona's specific guidance (1-3 paragraphs)
- One line about what the persona is paired against (for tone-calibration)

**Persona-specific guidance to embed:**

| Persona | Role statement core | Specific guidance |
|---------|---------------------|-------------------|
| Realist | Experienced operator who's seen plays like this play out. | Anchor on base rates. Name typical failure modes. Don't doom — predict. |
| Pre-mortem | A future version of the user, narrating from 18 months out, the story of how this went badly. | Story form. Concrete failure causes. What was the first crack? |
| Expander | A creative strategist whose job is to make the idea bigger and more exciting. | What's the 10x version? What's the audacious framing being missed? |
| Researcher | A research analyst. Your job is decision-altering evidence, not interesting reading. | Surface only facts that would change a mind. If none, say so plainly. Don't pad. |
| Devil's Advocate | A trained adversarial reviewer paid to find the strongest case against the apparent answer. | Steelman the rejected position. Find one objection that, if true, breaks the case. |
| First-Principles | A thinker who strips away the framing and asks what the actual underlying problem is. | Is the question the right question? Reframe if needed. |
| Stakeholder-Empathy | The voice of the people affected by this decision — including those not in the room. | Name who's affected. What does this look like from their side? |

**Step 2: Write each persona file** (follow the optimist.md pattern; use the guidance from the table).

**Step 3: Verify all 8 exist**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
ls advisors/personas/*.md | grep -v README | wc -l
# Expected: 8
```

**Step 4: Smoke-test 2 random new personas via mol-advisor-run** (repeat Task 5 for two of the new ones — recommend Realist and Pre-mortem since they're voicier).

**Step 5: Commit**

```bash
git add advisors/personas/*.md
git commit -m "Add remaining 7 personas (Realist, Pre-mortem, Expander, Researcher,
Devil's Advocate, First-Principles, Stakeholder-Empathy)

Completes the v1 library of 8 personas. Each follows the format established
by optimist.md: shared hard-rules and output-format sections,
persona-specific role + guidance."
```

---

### Task 7: Parallel advisor dispatch (mol-council-fanout)

**Why:** The whole point of the system is parallel independent advisors. This formula slings N advisors at once and waits for all to return.

**Files:**
- Create: `/Users/adamdavidson/gt/.beads/formulas/mol-council-fanout.formula.toml`

**Step 1: Write the fanout formula**

```toml
description = "Sling N advisors in parallel on a council question, wait for all to return"
formula = "mol-council-fanout"
version = 1

[vars]

[vars.council_bead]
description = "The parent council bead ID"
required = true

[vars.personas]
description = "Comma-separated persona slugs (e.g., 'optimist,realist,pre-mortem')"
required = true

[vars.round]
description = "Round number"
default = "1"

[[steps]]
id = "validate"
title = "Validate inputs"
description = """
```bash
test -f /Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/01-question.md \
  || { echo "Missing 01-question.md for {{council_bead}}"; exit 1; }

IFS=',' read -ra PERSONAS <<< "{{personas}}"
for p in "${PERSONAS[@]}"; do
  test -f /Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/$p.md \
    || { echo "Persona not found: $p"; exit 1; }
done
echo "validated ${#PERSONAS[@]} personas"
```
"""

[[steps]]
id = "sling-all"
title = "Sling each persona to a fresh polecat"
needs = ["validate"]
description = """
```bash
IFS=',' read -ra PERSONAS <<< "{{personas}}"
for p in "${PERSONAS[@]}"; do
  gt sling "{{council_bead}}" advisor_machine/polecats \
    --formula mol-advisor-run \
    --vars "council_bead={{council_bead}},persona=$p,round={{round}}" \
    --detach
done
echo "slung ${#PERSONAS[@]} advisors"
```
"""

[[steps]]
id = "wait-all"
title = "Wait for all advisor outputs to land"
needs = ["sling-all"]
description = """
```bash
IFS=',' read -ra PERSONAS <<< "{{personas}}"
DIR=/Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/advisors/round-{{round}}

# Poll up to 30 minutes (long enough for Claude polecat sessions). Break early
# when all are present.
for i in $(seq 1 180); do
  missing=0
  for p in "${PERSONAS[@]}"; do
    test -f "$DIR/$p.md" || missing=$((missing+1))
  done
  if [ $missing -eq 0 ]; then
    echo "all ${#PERSONAS[@]} returned (took $((i*10))s)"
    exit 0
  fi
  echo "waiting: $missing/${#PERSONAS[@]} still out"
  sleep 10
done

echo "TIMEOUT: still missing $missing advisors after 30min"
exit 1
```
"""
```

**Step 2: Verify formula loads**

```bash
gt formulas | grep council-fanout
```

**Step 3: Smoke test with 3 personas**

Reuse `$TEST_BEAD` from Task 5 (or create a new one). Run the fanout formula manually:

```bash
gt sling $TEST_BEAD mayor --formula mol-council-fanout \
  --vars "council_bead=$TEST_BEAD,personas=optimist,realist,pre-mortem,round=1"
```

Wait. Verify all 3 advisor files appear in the bead's round-1 dir.

**Step 4: Spot-check the 3 outputs**

```bash
for p in optimist realist pre-mortem; do
  echo "=== $p ==="
  cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/advisors/round-1/$p.md | head -5
done
```

Expected: three independent voices, no cross-references between them.

**Step 5: Commit**

```bash
cd /Users/adamdavidson/gt
git add .beads/formulas/mol-council-fanout.formula.toml
git commit -m "Add mol-council-fanout formula for parallel advisor dispatch

Slings each persona to a fresh polecat (isolated context, no cross-talk),
then polls .runtime/councils/<bead>/advisors/round-N/ until all files
land or a 30-minute timeout fires."
```

---

### Task 8: Synthesizer (mol-council-synth)

**Why:** Reads all advisor outputs from a round, produces the crux + consensus + tensions + proposed follow-ups.

**Files:**
- Create: `advisors/personas/synthesizer.md` (the synth's system prompt — kept alongside personas though it's not selectable)
- Create: `/Users/adamdavidson/gt/.beads/formulas/mol-council-synth.formula.toml`

**Step 1: Write `advisors/personas/synthesizer.md`**

```markdown
---
name: synthesizer
display: The Synthesizer
description: Reads all advisor outputs in a round, finds the crux. Internal — not user-selectable.
---

You are the Synthesizer. You receive the outputs of N independent advisors
who could not see each other. Your job is NOT to summarize. Your job is to
find the **crux**: the single fact, assumption, or value judgment that, if
resolved, would settle this question. Everything else is supporting material.

You are not a writer. You are an analyst.

## Hard rules (do not violate)

- Do not summarize advisor-by-advisor. The reader can read the originals.
- "There were many perspectives" is failure. Identify the load-bearing tension.
- If you find no real disagreement, say so — and proceed to propose finalization.

## Output format

Return a markdown file with these sections, in this order:

### The crux
<one or two sentences: the single thing that, if resolved, settles this>

### Where the council agreed
<bullets — genuine consensus only, not absence of disagreement>

### Where the council split
For each real split, name which advisors held which position and why.

### The strongest single objection
<one paragraph — the one thing that, if true, breaks the apparent case>

### Proposed follow-ups (if any)
For each follow-up, specify which advisor(s) should answer and the exact
question. If you propose zero follow-ups, say so plainly and recommend
proceeding to scribe.

### Convergence read
One of:
- `tension-surfaced` — real disagreement, follow-up may help
- `consensus-fast` — converged on round 1, no real tension
- `inconclusive` — advisors didn't engage substantively, more clarity needed
```

**Step 2: Write `mol-council-synth.formula.toml`**

```toml
description = "Read all advisor outputs from a round, produce the synthesis"
formula = "mol-council-synth"
version = 1

[vars]

[vars.council_bead]
description = "The parent council bead ID"
required = true

[vars.round]
description = "Round number to synthesize"
default = "1"

[[steps]]
id = "gather"
title = "Read all advisor outputs"
description = """
```bash
DIR=/Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/advisors/round-{{round}}
test -d "$DIR" || { echo "Missing round dir: $DIR"; exit 1; }
ls "$DIR"/*.md
```

Read every .md file in the round dir. Also read 01-question.md for context.
"""

[[steps]]
id = "synthesize"
title = "Produce synthesis"
needs = ["gather"]
description = """
Adopt the Synthesizer persona at
`/Users/adamdavidson/gt/advisor_machine/crew/adamd/advisors/personas/synthesizer.md`.

Following its required output format, produce the synthesis. Write to:
`/Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/synth/round-{{round}}.md`

Then attach to the bead:
```bash
bd update {{council_bead}} --append-notes "## synth/round-{{round}}.md attached
$(cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/synth/round-{{round}}.md)"
```
"""
```

**Step 3: Smoke test on the existing test bead** (has 3 advisor outputs from Task 7)

```bash
gt sling $TEST_BEAD advisor_machine/polecats \
  --formula mol-council-synth \
  --vars "council_bead=$TEST_BEAD,round=1"

# Wait for synth/round-1.md to appear
until [ -f /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/synth/round-1.md ]; do
  sleep 5
done
cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/synth/round-1.md
```

**Step 4: Review checklist**

- [ ] Has a `### The crux` section with a real claim
- [ ] Does NOT summarize advisor-by-advisor
- [ ] Convergence read is one of the three valid values
- [ ] Proposed follow-ups (if any) target specific advisors

**Step 5: Commit**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git add advisors/personas/synthesizer.md
git commit -m "Add Synthesizer persona definition"

cd /Users/adamdavidson/gt
git add .beads/formulas/mol-council-synth.formula.toml
git commit -m "Add mol-council-synth formula

Reads advisor outputs from a round, produces crux + consensus + split +
strongest objection + proposed follow-ups + convergence read."
```

---

### Task 9: Scribe (mol-council-scribe)

**Why:** Final memo. Reads everything, applies verdict logic, writes the memo to bead and vault.

**Files:**
- Create: `advisors/personas/scribe.md`
- Create: `/Users/adamdavidson/gt/.beads/formulas/mol-council-scribe.formula.toml`

**Step 1: Write `advisors/personas/scribe.md`** (includes the memo template from spec §5, the "so what" gate, and the verdict-assignment logic).

Key content to include in the scribe's prompt:

- The full memo template (frontmatter + sections, copied from design spec §5)
- Verdict rules: 🟢 resolved (high-confidence non-obvious answer), 🟡 sharpened (didn't resolve, surfaced real crux), 🔴 inconclusive (didn't move forward)
- The "so what" gate: before writing the memo, answer in one sentence "if you only read the TL;DR, what would you do differently than before you asked?" If you can't, the memo is 🔴.
- Forbidden behaviors: adding own opinion, smoothing real disagreement, recommending actions unless asked.

**Step 2: Write `mol-council-scribe.formula.toml`**

Two key steps:
1. `gather`: read 01-question.md, all advisor files across all rounds, all synth files, all round-decision files.
2. `write-memo`: produce `99-memo.md`, attach to bead, copy to vault path.

The vault copy step (Phase 0 minimum: a single fixed vault path):
```bash
SLUG=$(grep -oP '^topic:\s*\K.*' .../99-memo.md || echo "council-$BEAD")
mkdir -p ~/ADSB/Council
cp /Users/adamdavidson/gt/advisor_machine/.runtime/councils/{{council_bead}}/99-memo.md \
   ~/ADSB/Council/$(date +%Y-%m-%d)-$SLUG.md \
  || echo "WARN: vault write failed; memo lives in bead only"
```

**Step 3: Smoke test**

```bash
gt sling $TEST_BEAD advisor_machine/polecats \
  --formula mol-council-scribe \
  --vars "council_bead=$TEST_BEAD"

until [ -f /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/99-memo.md ]; do
  sleep 5
done
cat /Users/adamdavidson/gt/advisor_machine/.runtime/councils/$TEST_BEAD/99-memo.md
ls ~/ADSB/Council/ | tail -3
```

**Step 4: Review checklist**

- [ ] Memo has all required sections (TL;DR, agreed, split, crux, objection, learn-next, outliers)
- [ ] Verdict field is one of 🟢🟡🔴
- [ ] Vault file exists at `~/ADSB/Council/YYYY-MM-DD-<slug>.md`
- [ ] Frontmatter `council:` field points to the bead

**Step 5: Commit**

```bash
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git add advisors/personas/scribe.md
git commit -m "Add Scribe persona — final memo writer with verdict logic"

cd /Users/adamdavidson/gt
git add .beads/formulas/mol-council-scribe.formula.toml
git commit -m "Add mol-council-scribe formula

Reads all council artifacts, writes 99-memo.md with calibrated verdict
(🟢/🟡/🔴) per spec §5, copies polished memo to ~/ADSB/Council/."
```

---

### Task 10: Wire the `/council` slash command to dispatch

**Why:** Replace the Phase 0 stub in `council.md` (Task 2) with real dispatch logic. After lineup approval, the command should: create council bead, write intake + question + lineup, sling fanout, wait, sling synth, present synth + skip-loop for Phase 0, sling scribe.

**Files:**
- Modify: `/Users/adamdavidson/gt/mayor/.claude/commands/council.md`

**Step 1: Replace the "After approval" block in council.md**

Add a concrete dispatch sequence:

```markdown
## After approval (Phase 0 — no follow-up loop)

1. Create the council bead:
   ```bash
   COUNCIL_BEAD=$(bd create "Council: <slug>" --type task ... | grep -oE "am-[a-z0-9]+")
   ```
2. Write intake/question/lineup via the helpers:
   ```bash
   source /Users/adamdavidson/gt/advisor_machine/crew/adamd/scripts/council-bead.sh
   write_intake "$COUNCIL_BEAD" "..."
   write_question "$COUNCIL_BEAD" "..."
   write_lineup "$COUNCIL_BEAD" "..."
   ```
3. Sling fanout:
   ```bash
   gt sling $COUNCIL_BEAD mayor --formula mol-council-fanout \
     --vars "council_bead=$COUNCIL_BEAD,personas=$LINEUP,round=1"
   ```
4. Wait for fanout to complete (poll round-1 dir).
5. Sling synth:
   ```bash
   gt sling $COUNCIL_BEAD advisor_machine/polecats \
     --formula mol-council-synth --vars "council_bead=$COUNCIL_BEAD,round=1"
   ```
6. Wait for `synth/round-1.md`. Present it to the user.
7. **For Phase 0, skip the approve-loop.** Go straight to scribe.
8. Sling scribe:
   ```bash
   gt sling $COUNCIL_BEAD advisor_machine/polecats \
     --formula mol-council-scribe --vars "council_bead=$COUNCIL_BEAD"
   ```
9. Wait for `99-memo.md`. Report path + verdict to user.
```

**Step 2: End-to-end smoke test with a real question**

In a fresh Mayor Claude Code session: `/council "Should I split my morning routine into two parts?"` — complete intake, approve a lineup of 3 personas, watch the full pipeline run end-to-end.

Time it. Expect 5-15 minutes wall-clock for 3 advisors + synth + scribe with current Claude polecat latency.

**Step 3: Review checklist**

- [ ] Council bead exists with all artifacts attached
- [ ] Vault note exists at expected path
- [ ] Memo verdict is one of 🟢🟡🔴
- [ ] No advisor referenced another advisor's name
- [ ] Mayor's context did not contain raw advisor outputs (only the synth + memo)

**Step 4: Commit**

```bash
git add /Users/adamdavidson/gt/mayor/.claude/commands/council.md 2>/dev/null || true
cd /Users/adamdavidson/gt/advisor_machine/crew/adamd
git commit --allow-empty -m "Wire /council to full Phase 0 pipeline

Intake → fanout → synth → scribe. No follow-up loop yet (Phase 1).
Smoke test passed on real question with 3 advisors."
```

---

### Task 11: Phase 0 documentation

**Why:** Record what shipped, what's known to work, and the v1 backlog for Phase 1.

**Files:**
- Modify: `README.md` (in `crew/adamd/`)
- Create: `docs/PHASE-0.md`

**Step 1: Update `README.md`** with a brief "what this is" + pointer to the design spec.

**Step 2: Write `docs/PHASE-0.md`** — short. What's done, what works, the known limitations (no loop, no forced dissent, hardcoded vault path), and link to bead `am-qvl` for the v1 epic.

**Step 3: Update the spec status**

Change frontmatter of `docs/plans/2026-05-10-advisor-machine-design.md`:
```
status: draft (v1) → phase-0 shipped
```

**Step 4: Commit + push**

```bash
git add README.md docs/PHASE-0.md docs/plans/2026-05-10-advisor-machine-design.md
git commit -m "Phase 0 shipped — pipeline runs end-to-end

Known limitations (deferred to Phase 1):
- No synth-propose / user-approve loop
- No forced-dissent advisor
- Verdict logic is in the scribe but unverified across many councils"
git pull --rebase
git push
cd /Users/adamdavidson/gt
git pull --rebase
git push  # for the town-level formula commits
```

**Step 5: Update bead status**

```bash
bd update am-qvl --append-notes "Phase 0 shipped. Tasks 1-11 complete. Moving to Phase 1." 
```

---

## Phase 1 — Loop + Polish

### Task 12: Synth-approve loop in council.md

After step 6 of the Phase 0 dispatch (present synth to user), instead of jumping to scribe:

1. Present synth + proposed follow-ups.
2. Ask user: approve round 2, edit follow-ups, or skip to scribe.
3. If approve: sling `mol-council-fanout` again with only the targeted advisors (each gets their *own* prior round's output injected as context — see §6 hard rule on cross-advisor contamination).
4. Sling synth again on round 2.
5. Repeat until user skips or synth convergence read is `consensus-fast` / `inconclusive`.

Files: Modify `council.md`. Add a round-2 dispatch path. Add `--vars "prior_output_file=.../optimist.md"` style to `mol-advisor-run` so an advisor can see *only their own* prior reasoning in follow-up rounds.

Smoke test: run a real council, approve round 2, verify round-2 advisors only see their own round-1 output (grep their context).

Commit + push.

---

### Task 13: Forced-dissent advisor

Modify `mol-council-synth` to set a flag in its output when convergence_read is `consensus-fast`. Modify `council.md` to read that flag and, if set, sling one extra advisor: `mol-advisor-run` with `persona=opposition` (new persona).

Files:
- Create: `advisors/personas/opposition.md` (the Strongest Opposing Case)
- Modify: `mol-council-synth.formula.toml` (emit a flag file)
- Modify: `council.md` (read flag, dispatch opposition if set)

Smoke test: run a council on a question with an obviously-correct answer; verify opposition gets slung and produces a real steelman.

Commit + push.

---

### Task 14: `/council reject` subcommand

Allow the user to abort a council mid-flight with a reason, recording it to the bead.

Files: Modify `council.md`. Add subcommand handling. Could split into a separate `/council-reject` if `$ARGUMENTS`-based subcommands prove unwieldy.

Commit + push.

---

### Task 15: Phase 1 documentation + bead close

- Update `docs/PHASE-0.md` → `docs/PHASE-1.md` with what shipped in Phase 1.
- Update spec frontmatter to `status: v1 shipped`.
- Close `am-qvl` with a comment summarizing what's in v1 and pointing at any follow-up beads (Phase 2 dogfooding observations, v2 features).

Commit + push.

---

## Open Questions for the Implementer

These should be resolved as Task 0 (before Task 1) or by reading the gt source if accessible:

1. **Exact `gt sling --vars` syntax.** The plan assumes `--vars "key1=val1,key2=val2"`. If the real syntax differs (e.g., repeated `--var key=val`), all formula dispatch commands need updating.
2. **How a polecat formula reads `{{var}}` interpolations.** Confirm by inspecting an existing formula (e.g., `mol-deacon-patrol`) and tracing how its vars get into the polecat's session.
3. **Whether `--formula <name>` is the right flag on `gt sling`.** If it's a different flag (e.g., `--mol`, `--molecule`), update all dispatch commands.
4. **Wait/notification mechanism between Mayor and polecat completions.** Plan uses file-existence polling on `.runtime/...` files. If gt provides a cleaner mechanism (mail, hook events), prefer that.
5. **Where `advisor_machine/polecats` vs `advisor_machine/advisors` is correct as a sling target.** Plan uses `advisor_machine/polecats` (existing dir); confirm against gt's expected sling-target format.

If any of these break a step, fix the helper script / formulas / slash command and propagate the fix back into the plan as an amendment commit.

---

## Verification Summary

By end of Phase 0:
- [ ] `/council "..."` runs end-to-end on a real question
- [ ] One council bead per question with full artifact layout
- [ ] Vault note at `~/ADSB/Council/YYYY-MM-DD-<slug>.md`
- [ ] Memo carries a 🟢🟡🔴 verdict
- [ ] No cross-advisor context contamination (grep advisor session logs for other persona names — should be zero hits)
- [ ] `am-qvl` updated with Phase 0 shipped status

By end of Phase 1:
- [ ] Synth-approve loop works; user can approve, edit, or skip round 2
- [ ] Forced-dissent advisor fires when synth flags `consensus-fast`
- [ ] `/council reject` aborts cleanly with reason recorded
- [ ] `am-qvl` closed
