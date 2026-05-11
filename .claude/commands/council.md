---
description: Start an Advisor Machine council skeleton
argument-hint: "<question>"
allowed-tools: Bash(*)
---

# /council

Start an Advisor Machine council skeleton for the user's question.

Question: $ARGUMENTS

Execute this command:

```bash
ADVISOR_MACHINE_REPO="${ADVISOR_MACHINE_REPO:-/Users/adamdavidson/gt/advisor_machine/crew/adamd}"
cd "$ADVISOR_MACHINE_REPO" && PYTHONPATH=src python3 -m advisor_machine.council "$ARGUMENTS"
```

Return the printed skeleton path to the user. The Phase 0 scaffold creates the
artifact directories and placeholder files; later pipeline beads fill them.
