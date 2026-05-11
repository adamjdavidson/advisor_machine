---
description: Start an Advisor Machine council pipeline
argument-hint: "<question>"
allowed-tools: Bash(*)
---

# /council

Start an Advisor Machine council for the user's question.

Question: $ARGUMENTS

First run intake in the chat:

1. Ask one clarifying question at a time until you have:
   - the decision or output needed,
   - the key constraints and context,
   - what a useful answer would change.
2. Draft the advisor lineup and ask for approval.
3. After approval, execute this command with one `--answer` flag per intake
   answer:

```bash
ADVISOR_MACHINE_REPO="${ADVISOR_MACHINE_REPO:-/Users/adamdavidson/gt/advisor_machine/crew/adamd}"
cd "$ADVISOR_MACHINE_REPO" && PYTHONPATH=src python3 -m advisor_machine.council \
  --answer "<decision/output answer>" \
  --answer "<constraints/context answer>" \
  --answer "<usefulness answer>" \
  --yes \
  "$ARGUMENTS"
```

Return the printed council paths to the user. The Phase 0 pipeline writes
intake, isolated advisor prompts and outputs, synth, scribe memo, and vault
memo artifacts.
