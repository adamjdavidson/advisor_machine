# Advisor Machine

Advisor Machine turns a fuzzy question into a council of isolated advisor
agents, then preserves the transcript and final memo. This repo currently
contains the Phase 0 vertical pipeline for `/council`.

## Quick Start

Run the command without installing anything:

```bash
PYTHONPATH=src python3 -m advisor_machine.council "Should I hire a COO?"
```

Or use the script launcher:

```bash
./scripts/council "Should I hire a COO?"
```

The command creates a draft council skeleton under `.advisor_machine/councils/`
then runs one intake, advisor, synth, and scribe pass. It writes the final memo
into the council directory and copies the vault memo to `~/ADSB/Council/`.

For non-interactive runs, provide intake answers and approve the lineup:

```bash
PYTHONPATH=src python3 -m advisor_machine.council \
  --answer "Decision memo." \
  --answer "12 people, $3M ARR, mostly engineers." \
  --answer "Find the cheapest test before hiring." \
  --yes \
  "Should I hire a COO?"
```

## Slash Command

The repo includes `.claude/commands/council.md`, a Claude slash-command shim for
`/council`. The command runs the same Python scaffold and reports the skeleton
path. Set `ADVISOR_MACHINE_REPO` if the repo is not at the default local path.

## Tests

```bash
python3 -m unittest tests.test_council_skeleton -v
```

## Layout

See `docs/PROJECT_LAYOUT.md` for where personas, council artifacts, synth
outputs, scribe outputs, and vault writes live.
