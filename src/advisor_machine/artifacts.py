"""Filesystem artifact writers for Advisor Machine council runs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AdvisorOutput:
    round_number: int
    advisor_slug: str
    markdown: str


@dataclass(frozen=True)
class SynthOutput:
    round_number: int
    markdown: str
    decision_markdown: str | None = None


@dataclass(frozen=True)
class Memo:
    title: str
    body_markdown: str
    verdict: str


@dataclass(frozen=True)
class CouncilRun:
    council_id: str
    date: str
    topic: str
    tags: list[str]
    refined_question: str
    constraints: list[str]
    intake_markdown: str
    lineup_markdown: str
    advisor_outputs: list[AdvisorOutput]
    synth_outputs: list[SynthOutput]
    memo: Memo

    @property
    def round_count(self) -> int:
        rounds = [output.round_number for output in self.advisor_outputs]
        rounds.extend(output.round_number for output in self.synth_outputs)
        return max(rounds, default=0)

    @property
    def advisor_slugs(self) -> list[str]:
        seen = set()
        ordered = []
        for output in self.advisor_outputs:
            if output.advisor_slug in seen:
                continue
            seen.add(output.advisor_slug)
            ordered.append(output.advisor_slug)
        return ordered


@dataclass(frozen=True)
class CouncilArtifactResult:
    council_dir: Path
    bead_memo_path: Path
    vault_path: Path
    vault_written: bool
    vault_error: str | None
    report_message: str


class CouncilArtifactLedger:
    """Writes one permanent artifact directory per council bead."""

    def __init__(self, artifact_root: Path | str, vault_root: Path | str | None = None):
        self.artifact_root = Path(artifact_root).expanduser()
        self.vault_writer = VaultMemoWriter(vault_root)

    def write_run(self, run: CouncilRun) -> CouncilArtifactResult:
        council_dir = self.artifact_root / run.council_id
        council_dir.mkdir(parents=True, exist_ok=True)

        self._write(council_dir / "00-intake.md", run.intake_markdown)
        self._write(council_dir / "01-question.md", self._question_markdown(run))
        self._write(council_dir / "02-lineup.md", run.lineup_markdown)
        self._write_advisor_outputs(council_dir, run.advisor_outputs)
        self._write_synth_outputs(council_dir, run.synth_outputs)

        memo_markdown = render_memo(run)
        bead_memo_path = council_dir / "99-memo.md"
        self._write(bead_memo_path, memo_markdown)

        return self.vault_writer.write(run, memo_markdown, council_dir, bead_memo_path)

    def _write_advisor_outputs(self, council_dir: Path, outputs: Iterable[AdvisorOutput]) -> None:
        for output in outputs:
            path = (
                council_dir
                / "advisors"
                / f"round-{output.round_number}"
                / f"{slugify(output.advisor_slug)}.md"
            )
            self._write(path, output.markdown)

    def _write_synth_outputs(self, council_dir: Path, outputs: Iterable[SynthOutput]) -> None:
        for output in outputs:
            round_path = council_dir / "synth" / f"round-{output.round_number}.md"
            self._write(round_path, output.markdown)
            if output.decision_markdown is not None:
                decision_path = council_dir / "synth" / f"round-{output.round_number}-decision.md"
                self._write(decision_path, output.decision_markdown)

    def _question_markdown(self, run: CouncilRun) -> str:
        constraints = _markdown_list(run.constraints) if run.constraints else "None listed."
        tags = _markdown_list(run.tags) if run.tags else "None listed."
        return "\n".join(
            [
                "# Refined question",
                "",
                run.refined_question,
                "",
                "## Constraints",
                "",
                constraints,
                "",
                "## Topic tags",
                "",
                tags,
            ]
        )

    def _write(self, path: Path, markdown: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_with_trailing_newline(markdown), encoding="utf-8")


class VaultMemoWriter:
    """Copies the polished memo to the user's Obsidian council vault."""

    def __init__(self, vault_root: Path | str | None = None):
        if vault_root is None:
            vault_root = Path.home() / "ADSB" / "Council"
        self.vault_root = Path(vault_root).expanduser()

    def write(
        self,
        run: CouncilRun,
        memo_markdown: str,
        council_dir: Path,
        bead_memo_path: Path,
    ) -> CouncilArtifactResult:
        vault_path = self.vault_root / f"{run.date}-{slugify(run.topic)}.md"
        try:
            vault_path.parent.mkdir(parents=True, exist_ok=True)
            vault_path.write_text(_with_trailing_newline(memo_markdown), encoding="utf-8")
        except OSError as exc:
            error = str(exc)
            return CouncilArtifactResult(
                council_dir=council_dir,
                bead_memo_path=bead_memo_path,
                vault_path=vault_path,
                vault_written=False,
                vault_error=error,
                report_message=f"Vault write failed: {error}. Memo remains in bead: {bead_memo_path}",
            )

        return CouncilArtifactResult(
            council_dir=council_dir,
            bead_memo_path=bead_memo_path,
            vault_path=vault_path,
            vault_written=True,
            vault_error=None,
            report_message=f"Memo written to {vault_path}. Full transcript: {bead_memo_path}",
        )


def render_memo(run: CouncilRun) -> str:
    frontmatter = [
        "---",
        f"council: {run.council_id}",
        f"date: {run.date}",
        f"topic: {slugify(run.topic)}",
        f"tags: {_frontmatter_list(run.tags)}",
        f"rounds: {run.round_count}",
        f"advisors: {_frontmatter_list(run.advisor_slugs)}",
        f"verdict: {run.memo.verdict}",
        "---",
        "",
    ]
    body = [
        f"# {run.memo.title}",
        "",
        run.memo.body_markdown.strip(),
        "",
        "---",
        f"*Full transcript: bead {run.council_id}*",
    ]
    return "\n".join(frontmatter + body)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _frontmatter_list(values: Iterable[str]) -> str:
    return "[" + ", ".join(values) + "]"


def _markdown_list(values: Iterable[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def _with_trailing_newline(markdown: str) -> str:
    return markdown if markdown.endswith("\n") else f"{markdown}\n"
