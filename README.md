# Advisor Machine

Advisor Machine turns a fuzzy question into a council of isolated advisor
agents, then preserves the transcript and final memo. This repo currently
contains the Phase 0 command scaffold for `/council`.

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
and prints the eventual vault memo target under `~/ADSB/Council/`.

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
