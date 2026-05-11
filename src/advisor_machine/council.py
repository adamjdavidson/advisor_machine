"""Phase 0 command surface for Advisor Machine councils."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


PERSONAS: tuple[tuple[str, str], ...] = (
    ("optimist", "Optimist"),
    ("realist", "Realist"),
    ("pre-mortem", "Pre-mortem"),
    ("expander", "Expander"),
    ("researcher", "Researcher"),
    ("devils-advocate", "Devil's Advocate"),
    ("first-principles", "First-Principles"),
    ("stakeholder-empathy", "Stakeholder-Empathy"),
)


@dataclass(frozen=True)
class CouncilSkeleton:
    """Paths created or reported for a new council draft."""

    question: str
    council_id: str
    council_dir: Path
    vault_path: Path
    files: dict[str, Path]


def slugify(value: str, *, max_words: int = 9) -> str:
    """Return a stable, readable slug from user-supplied council text."""

    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return "council"
    return "-".join(tokens[:max_words])


def build_council_skeleton(
    question: str,
    *,
    state_dir: str | Path | None = None,
    vault_dir: str | Path | None = None,
    now: datetime | None = None,
    create: bool = True,
) -> CouncilSkeleton:
    """Create a Phase 0 council artifact skeleton and return its paths."""

    normalized_question = " ".join(question.split())
    if not normalized_question:
        raise ValueError('question is required, e.g. /council "Should I hire a COO?"')

    timestamp = now or datetime.now().astimezone()
    slug = slugify(normalized_question)
    council_id = f"draft-{timestamp:%Y%m%d-%H%M%S}-{slug}"

    state_root = Path(
        state_dir or os.environ.get("ADVISOR_MACHINE_STATE_DIR", ".advisor_machine")
    ).expanduser()
    vault_root = Path(
        vault_dir or os.environ.get("ADVISOR_MACHINE_VAULT_DIR", "~/ADSB/Council")
    ).expanduser()

    council_dir = state_root / "councils" / council_id
    vault_path = vault_root / f"{timestamp:%Y-%m-%d}-{slug}.md"

    files = {
        "intake": council_dir / "00-intake.md",
        "question": council_dir / "01-question.md",
        "lineup": council_dir / "02-lineup.md",
        "advisor_round": council_dir / "advisors" / "round-1",
        "synth": council_dir / "synth",
        "memo": council_dir / "99-memo.md",
    }

    skeleton = CouncilSkeleton(
        question=normalized_question,
        council_id=council_id,
        council_dir=council_dir,
        vault_path=vault_path,
        files=files,
    )

    if create:
        _write_skeleton_files(skeleton)

    return skeleton


def format_skeleton(skeleton: CouncilSkeleton, *, created: bool = True) -> str:
    """Render the command result for a Mayor-facing slash command."""

    status = "ready" if created else "preview"
    lines = [
        f"Council skeleton {status}",
        f"Question: {skeleton.question}",
        f"Council ID: {skeleton.council_id}",
        f"Skeleton: {skeleton.council_dir}",
        "Artifacts:",
        f"  intake: {skeleton.files['intake']}",
        f"  refined question: {skeleton.files['question']}",
        f"  lineup: {skeleton.files['lineup']}",
        f"  advisor outputs: {skeleton.files['advisor_round']}",
        f"  synth outputs: {skeleton.files['synth']}",
        f"  scribe memo: {skeleton.files['memo']}",
        f"Vault target: {skeleton.vault_path}",
        "Status: Phase 0 scaffold only; later pipeline beads fill these artifacts.",
    ]
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="/council",
        description="Create an Advisor Machine council artifact skeleton.",
    )
    parser.add_argument("question", nargs="*", help="initial council question")
    parser.add_argument(
        "--state-dir",
        help="runtime state root; defaults to ADVISOR_MACHINE_STATE_DIR or .advisor_machine",
    )
    parser.add_argument(
        "--vault-dir",
        help="vault memo directory; defaults to ADVISOR_MACHINE_VAULT_DIR or ~/ADSB/Council",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="print paths without creating runtime files",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    question = " ".join(args.question)

    try:
        skeleton = build_council_skeleton(
            question,
            state_dir=args.state_dir,
            vault_dir=args.vault_dir,
            create=not args.preview,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(format_skeleton(skeleton, created=not args.preview))
    return 0


def _write_skeleton_files(skeleton: CouncilSkeleton) -> None:
    skeleton.files["advisor_round"].mkdir(parents=True, exist_ok=True)
    skeleton.files["synth"].mkdir(parents=True, exist_ok=True)

    _write_text(
        skeleton.files["intake"],
        "\n".join(
            [
                "# Intake",
                "",
                "## Original question",
                "",
                f"> {skeleton.question}",
                "",
                "## Clarifying transcript",
                "",
                "Phase 0 scaffold: conversational intake is not implemented yet.",
                "",
            ]
        ),
    )
    _write_text(
        skeleton.files["question"],
        "\n".join(
            [
                "# Refined Question",
                "",
                f"Initial question: {skeleton.question}",
                "",
                "Constraints: Phase 0 scaffold placeholder.",
                "Topic tags: []",
                "",
            ]
        ),
    )
    _write_text(
        skeleton.files["lineup"],
        "\n".join(
            [
                "# Advisor Lineup",
                "",
                *[f"- {display} (`{slug}`)" for slug, display in PERSONAS],
                "",
                "Phase 0 scaffold: intake has not selected or edited this lineup yet.",
                "",
            ]
        ),
    )
    _write_text(skeleton.files["advisor_round"] / ".gitkeep", "")
    _write_text(skeleton.files["synth"] / ".gitkeep", "")
    _write_text(
        skeleton.files["memo"],
        "\n".join(
            [
                "---",
                f"council: {skeleton.council_id}",
                f"vault_target: {skeleton.vault_path}",
                "verdict: pending",
                "---",
                "",
                f"# {skeleton.question}",
                "",
                "Phase 0 scaffold: scribe output is not implemented yet.",
                "",
            ]
        ),
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
