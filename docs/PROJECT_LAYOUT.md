# Advisor Machine Project Layout

Advisor Machine v1 starts with a small command surface and a stable place for
future orchestration code to write council artifacts.

## Command Surface

| Path | Purpose |
| --- | --- |
| `.claude/commands/council.md` | Claude slash-command shim for `/council` in a Mayor-style session. |
| `scripts/council` | Local launcher for the same command surface. |
| `src/advisor_machine/council.py` | Python stdlib CLI and skeleton artifact writer. |

The direct local invocation is:

```bash
PYTHONPATH=src python3 -m advisor_machine.council "Should I hire a COO?"
```

The script launcher is:

```bash
./scripts/council "Should I hire a COO?"
```

To make `/council` available from a Mayor Claude session, install or symlink
`.claude/commands/council.md` into the Mayor session command directory. The
command defaults `ADVISOR_MACHINE_REPO` to
`/Users/adamdavidson/gt/advisor_machine/crew/adamd`; set that environment
variable if the repo lives somewhere else.

## Source Layout

| Path | Purpose |
| --- | --- |
| `src/advisor_machine/__init__.py` | Package marker and version. |
| `src/advisor_machine/council.py` | `/council` Phase 0 skeleton implementation. |
| `src/advisor_machine/personas/*.md` | Version-controlled advisor persona library. |
| `tests/test_council_skeleton.py` | Command and artifact-layout tests. |

## Runtime Artifacts

Runtime state is intentionally ignored by git.

```text
.advisor_machine/
+-- councils/
    +-- draft-YYYYMMDD-HHMMSS-<slug>/
        +-- 00-intake.md
        +-- 01-question.md
        +-- 02-lineup.md
        +-- advisors/
        |   +-- round-1/
        |       +-- .gitkeep
        +-- synth/
        |   +-- .gitkeep
        +-- 99-memo.md
```

The default vault target is `~/ADSB/Council/YYYY-MM-DD-<slug>.md`. The Phase 0
command reports that path but does not write to the vault; the scribe bead will
own vault writes.

Environment overrides:

| Variable | Purpose |
| --- | --- |
| `ADVISOR_MACHINE_STATE_DIR` | Runtime state root. Defaults to `.advisor_machine`. |
| `ADVISOR_MACHINE_VAULT_DIR` | Memo vault target directory. Defaults to `~/ADSB/Council`. |
