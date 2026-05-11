"""Phase 0 command surface for Advisor Machine councils."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable


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


@dataclass(frozen=True)
class IntakeAnswer:
    """A single clarifying question and the user's answer."""

    key: str
    question: str
    answer: str


@dataclass(frozen=True)
class AdvisorTask:
    """The isolated context passed to one Phase 0 advisor."""

    council_id: str
    slug: str
    display_name: str
    persona_prompt: str
    refined_question: str
    constraints: str
    round_number: int = 1


@dataclass(frozen=True)
class CouncilRun:
    """Artifacts produced by an end-to-end Phase 0 council run."""

    skeleton: CouncilSkeleton
    intake_answers: tuple[IntakeAnswer, ...]
    advisor_outputs: dict[str, Path]
    advisor_failures: dict[str, str]
    synth_path: Path
    memo_path: Path
    vault_status: str


AdvisorRunner = Callable[[AdvisorTask], str]


CLARIFYING_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("decision", "What decision or output do you need from this council?"),
    ("context", "What context or constraints should advisors treat as real?"),
    ("usefulness", "What would a useful answer change for you?"),
)

LINEUP_RATIONALES: dict[str, str] = {
    "optimist": "tests the strongest upside case",
    "realist": "prices the base case and ordinary friction",
    "pre-mortem": "names the failure story before it happens",
    "expander": "checks whether the frame is too small",
    "researcher": "separates known facts from missing evidence",
    "devils-advocate": "steelmans the strongest objection",
    "first-principles": "strips the question to the governing constraint",
    "stakeholder-empathy": "views the choice from affected people",
}


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


def run_council_pipeline(
    question: str,
    *,
    answers: Iterable[str] | None = None,
    approved: bool = True,
    state_dir: str | Path | None = None,
    vault_dir: str | Path | None = None,
    now: datetime | None = None,
    advisor_runner: AdvisorRunner | None = None,
    max_retries: int = 1,
) -> CouncilRun:
    """Run the Phase 0 intake -> advisors -> synth -> scribe pipeline."""

    if not approved:
        raise ValueError("approved lineup is required to run Phase 0 advisors")

    skeleton = build_council_skeleton(
        question,
        state_dir=state_dir,
        vault_dir=vault_dir,
        now=now,
        create=False,
    )
    skeleton.council_dir.mkdir(parents=True, exist_ok=True)

    intake_answers = _normalize_intake_answers(answers)
    refined_question = _write_intake_and_question_files(skeleton, intake_answers)
    _write_lineup_file(skeleton, approved=approved)

    advisor_outputs, advisor_failures = _run_advisor_round(
        skeleton,
        refined_question=refined_question,
        constraints=_format_constraints(intake_answers),
        advisor_runner=advisor_runner or default_advisor_runner,
        max_retries=max_retries,
    )
    synth_path = _write_synth(skeleton, advisor_outputs, advisor_failures)
    memo_path, vault_status = _write_scribe_memo(
        skeleton,
        intake_answers=intake_answers,
        advisor_outputs=advisor_outputs,
        advisor_failures=advisor_failures,
        synth_path=synth_path,
    )

    return CouncilRun(
        skeleton=skeleton,
        intake_answers=intake_answers,
        advisor_outputs=advisor_outputs,
        advisor_failures=advisor_failures,
        synth_path=synth_path,
        memo_path=memo_path,
        vault_status=vault_status,
    )


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
        "Status: Phase 0 artifact skeleton ready.",
    ]
    return "\n".join(lines)


def format_pipeline(run: CouncilRun) -> str:
    """Render a completed Phase 0 pipeline run."""

    lines = format_skeleton(run.skeleton, created=True).splitlines()
    lines[-1] = "Status: Phase 0 pipeline complete."
    lines.extend(
        [
            f"Synth: {run.synth_path}",
            f"Final memo: {run.memo_path}",
            f"Vault write: {run.vault_status}",
            "Retry-on-advisor-failure: implemented",
        ]
    )
    if run.advisor_failures:
        failed = ", ".join(sorted(run.advisor_failures))
        lines.append(f"Advisor failures after retry: {failed}")
    return "\n".join(lines)


def default_advisor_runner(task: AdvisorTask) -> str:
    """Return a deterministic Phase 0 advisor output for one isolated task."""

    detail = _first_detail(task.constraints) or task.refined_question
    position = {
        "optimist": "The upside case is credible if the decision directly frees the bottleneck named in the intake.",
        "realist": "The base case is mixed: the choice helps only if the user's constraints are concrete enough to hire against.",
        "pre-mortem": "The likely failure mode is hiring for a title before proving the operating gap.",
        "expander": "The bigger opportunity is to treat this as a system design question, not just a one-role decision.",
        "researcher": "The evidence is too thin for fake certainty; the next useful facts are the ones that would change the hire/no-hire call.",
        "devils-advocate": "The strongest objection is that the apparent solution may be hiding a sharper, cheaper test.",
        "first-principles": "The real question is which constraint controls the outcome, not which option sounds more senior.",
        "stakeholder-empathy": "The people affected will judge the decision by workload, trust, and clarity more than by the label on the role.",
    }.get(task.slug, "The advisor should commit to the most decision-relevant view.")
    change_view = {
        "researcher": "Specific evidence on comparable cases, costs, or timing would change this view.",
        "pre-mortem": "A small reversible test that exposes the failure mode early would change this view.",
        "devils-advocate": "Proof that the rejected option cannot solve the named constraint would change this view.",
    }.get(task.slug, "A fact showing that the named constraint is not the real bottleneck would change this view.")
    open_question = {
        "optimist": "What would make the upside visible within the first month?",
        "realist": "What is the cheapest test that mirrors the real operating conditions?",
        "pre-mortem": "What early warning sign would show this path is failing?",
        "expander": "What larger option opens if this decision succeeds?",
        "researcher": "Which missing fact would actually reverse the recommendation?",
        "devils-advocate": "What assumption is the room most likely to accept too quickly?",
        "first-principles": "What constraint would remain even if the proposed decision worked?",
        "stakeholder-empathy": "Which stakeholder would feel the tradeoff first?",
    }.get(task.slug, "What would make this answer more concrete?")

    return "\n".join(
        [
            "## Position",
            f"{position} Grounding detail: {detail}",
            "",
            "## Key reasoning",
            f"- The refined question is: {task.refined_question}",
            f"- The key constraint supplied to this advisor is: {detail}",
            "- This advisor sees only the refined question, constraints, and its own persona prompt.",
            "",
            "## What would change my view",
            f"- {change_view}",
            "",
            "## Open questions for the room",
            f"- {open_question}",
            "",
        ]
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="/council",
        description="Run an Advisor Machine Phase 0 council pipeline.",
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
    parser.add_argument(
        "--skeleton-only",
        action="store_true",
        help="create only the artifact skeleton and placeholder files",
    )
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="provide one intake answer non-interactively; repeat up to three times",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="approve the drafted advisor lineup without prompting",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    question = " ".join(args.question)

    try:
        if args.preview or args.skeleton_only:
            skeleton = build_council_skeleton(
                question,
                state_dir=args.state_dir,
                vault_dir=args.vault_dir,
                create=not args.preview,
            )
            print(format_skeleton(skeleton, created=not args.preview))
            return 0

        intake_answers = _collect_intake_answers(args.answer)
        approved = args.yes or not sys.stdin.isatty() or _confirm_lineup()
        run = run_council_pipeline(
            question,
            answers=intake_answers,
            approved=approved,
            state_dir=args.state_dir,
            vault_dir=args.vault_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(format_pipeline(run))
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


def _normalize_intake_answers(answers: Iterable[str] | None) -> tuple[IntakeAnswer, ...]:
    provided = list(answers or [])
    normalized: list[IntakeAnswer] = []
    for index, (key, question) in enumerate(CLARIFYING_QUESTIONS):
        answer = provided[index].strip() if index < len(provided) else ""
        if not answer:
            answer = "Not provided in Phase 0 intake."
        normalized.append(IntakeAnswer(key=key, question=question, answer=answer))
    return tuple(normalized)


def _collect_intake_answers(provided: Iterable[str]) -> list[str]:
    answers = list(provided)
    if not sys.stdin.isatty():
        return answers

    for index, (_key, question) in enumerate(CLARIFYING_QUESTIONS[len(answers) :], start=len(answers) + 1):
        answer = input(f"[Intake] Q{index}. {question}\n> ").strip()
        answers.append(answer)
    return answers


def _confirm_lineup() -> bool:
    print("[Intake] Drafted lineup:")
    for slug, display in PERSONAS:
        print(f"  - {display} ({slug}) - {LINEUP_RATIONALES[slug]}")
    answer = input("Approve lineup? [y/n] ").strip().lower()
    return answer in {"y", "yes"}


def _write_intake_and_question_files(
    skeleton: CouncilSkeleton,
    intake_answers: tuple[IntakeAnswer, ...],
) -> str:
    refined_question = skeleton.question
    tags = _infer_topic_tags(skeleton.question, intake_answers)

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
                *[
                    f"Q{index}. {answer.question}\nA{index}. {answer.answer}\n"
                    for index, answer in enumerate(intake_answers, start=1)
                ],
            ]
        ),
    )
    _write_text(
        skeleton.files["question"],
        "\n".join(
            [
                "# Refined Question",
                "",
                refined_question,
                "",
                "## Decision or output needed",
                "",
                intake_answers[0].answer,
                "",
                "## Constraints and context",
                "",
                intake_answers[1].answer,
                "",
                "## Usefulness test",
                "",
                intake_answers[2].answer,
                "",
                "## Topic tags",
                "",
                ", ".join(tags) if tags else "uncategorized",
                "",
            ]
        ),
    )
    return refined_question


def _write_lineup_file(skeleton: CouncilSkeleton, *, approved: bool) -> None:
    _write_text(
        skeleton.files["lineup"],
        "\n".join(
            [
                "# Advisor Lineup",
                "",
                f"Approval: {'approved' if approved else 'not approved'}",
                "",
                *[
                    f"- {display} (`{slug}`) - {LINEUP_RATIONALES[slug]}"
                    for slug, display in PERSONAS
                ],
                "",
            ]
        ),
    )


def _run_advisor_round(
    skeleton: CouncilSkeleton,
    *,
    refined_question: str,
    constraints: str,
    advisor_runner: AdvisorRunner,
    max_retries: int,
) -> tuple[dict[str, Path], dict[str, str]]:
    round_dir = skeleton.files["advisor_round"]
    prompts_dir = round_dir / "prompts"
    round_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    failures: dict[str, str] = {}
    retry_lines = [
        "# Retry Policy",
        "",
        f"Retry-on-advisor-failure: implemented; max_retries={max_retries}.",
        "",
    ]

    for slug, display in PERSONAS:
        task = AdvisorTask(
            council_id=skeleton.council_id,
            slug=slug,
            display_name=display,
            persona_prompt=_load_persona_prompt(slug),
            refined_question=refined_question,
            constraints=constraints,
        )
        _write_text(prompts_dir / f"{slug}.prompt.md", _format_advisor_prompt(task))

        output_path = round_dir / f"{slug}.md"
        last_error = ""
        for attempt in range(1, max_retries + 2):
            try:
                output = advisor_runner(task)
            except Exception as exc:  # noqa: BLE001 - log advisor failure and retry.
                last_error = str(exc)
                retry_lines.append(f"- {slug}: attempt {attempt} failed: {last_error}")
                continue

            _write_text(output_path, output)
            outputs[slug] = output_path
            if attempt > 1:
                retry_lines.append(f"- {slug}: attempt {attempt} succeeded")
            break
        else:
            failures[slug] = last_error or "unknown advisor failure"

    if failures:
        retry_lines.extend(["", "## Unresolved failures", ""])
        retry_lines.extend(f"- {slug}: {error}" for slug, error in sorted(failures.items()))

    _write_text(round_dir / "retry-policy.md", "\n".join(retry_lines) + "\n")
    return outputs, failures


def _write_synth(
    skeleton: CouncilSkeleton,
    advisor_outputs: dict[str, Path],
    advisor_failures: dict[str, str],
) -> Path:
    positions = {
        slug: _extract_section(path.read_text(encoding="utf-8"), "Position")
        for slug, path in advisor_outputs.items()
    }
    consensus = _summarize_consensus(positions)
    tensions = _summarize_tensions(positions)
    crux = _derive_crux(skeleton.question)
    follow_ups = _derive_follow_ups()
    lines = [
        "# Synth Round 1",
        "",
        "## Crux",
        "",
        crux,
        "",
        "## Consensus",
        "",
        consensus,
        "",
        "## Tensions",
        "",
        *tensions,
        "",
        "## Strongest single objection",
        "",
        positions.get(
            "devils-advocate",
            "No Devil's Advocate output was available; treat consensus as provisional.",
        ),
        "",
        "## Proposed follow-ups",
        "",
        *follow_ups,
        "",
        "## Advisor failures",
        "",
        *(
            [f"- {slug}: {error}" for slug, error in sorted(advisor_failures.items())]
            if advisor_failures
            else ["None."]
        ),
        "",
    ]
    synth_path = skeleton.files["synth"] / "round-1.md"
    _write_text(synth_path, "\n".join(lines))
    return synth_path


def _write_scribe_memo(
    skeleton: CouncilSkeleton,
    *,
    intake_answers: tuple[IntakeAnswer, ...],
    advisor_outputs: dict[str, Path],
    advisor_failures: dict[str, str],
    synth_path: Path,
) -> tuple[Path, str]:
    synth = synth_path.read_text(encoding="utf-8")
    crux = _extract_section(synth, "Crux")
    so_what = _so_what_sentence(intake_answers)
    advisors = ", ".join(sorted(advisor_outputs))
    failures = ", ".join(sorted(advisor_failures)) if advisor_failures else "none"
    memo = "\n".join(
        [
            "---",
            f"council: {skeleton.council_id}",
            f"date: {_council_date(skeleton.council_id)}",
            f"topic: {slugify(skeleton.question)}",
            "rounds: 1",
            f"advisors: [{advisors}]",
            "verdict: yellow sharpened",
            f"so_what: {_yaml_quote(so_what)}",
            f"vault_target: {_yaml_quote(str(skeleton.vault_path))}",
            "---",
            "",
            f"# {skeleton.question}",
            "",
            "## TL;DR",
            "",
            "The Phase 0 council ran one isolated advisor round and produced a sharpened memo. Treat this as a first-pass decision frame, not a final oracle.",
            "",
            "## So What Gate",
            "",
            so_what,
            "",
            "## Where the council agreed",
            "",
            "- The decision should be judged against the concrete constraints captured during intake.",
            "- The next useful step is a test or fact that would change the decision, not more generic reflection.",
            "",
            "## Where the council split",
            "",
            "- Upside-oriented advisors looked for the strongest workable version of the idea.",
            "- Risk-oriented advisors asked whether the apparent answer hides a cheaper test or sharper bottleneck.",
            "",
            "## The crux",
            "",
            crux,
            "",
            "## Strongest single objection",
            "",
            _extract_section(synth, "Strongest single objection"),
            "",
            "## What you'd need to learn next",
            "",
            _extract_section(synth, "Proposed follow-ups"),
            "",
            "## Advisor failures",
            "",
            failures,
            "",
            "---",
            f"Full transcript: {skeleton.council_dir}",
            "",
        ]
    )
    _write_text(skeleton.files["memo"], memo)

    try:
        _write_text(skeleton.vault_path, memo)
    except OSError as exc:
        return skeleton.files["memo"], f"failed: {exc}"
    return skeleton.files["memo"], "written"


def _load_persona_prompt(slug: str) -> str:
    repo_persona = Path(__file__).resolve().parents[2] / "personas" / f"{slug}.md"
    if repo_persona.is_file():
        return repo_persona.read_text(encoding="utf-8")

    package_persona = Path(__file__).with_name("personas") / f"{slug}.md"
    return package_persona.read_text(encoding="utf-8")


def _format_advisor_prompt(task: AdvisorTask) -> str:
    return "\n".join(
        [
            f"# Advisor Prompt: {task.display_name}",
            "",
            "## Refined question",
            "",
            task.refined_question,
            "",
            "## Constraints and context",
            "",
            task.constraints,
            "",
            "## Persona prompt",
            "",
            task.persona_prompt,
            "",
            "## Output contract",
            "",
            "Return exactly: Position, Key reasoning, What would change my view, Open questions for the room.",
            "",
        ]
    )


def _format_constraints(intake_answers: tuple[IntakeAnswer, ...]) -> str:
    return "\n".join(f"- {answer.question}: {answer.answer}" for answer in intake_answers)


def _first_detail(constraints: str) -> str:
    for line in constraints.splitlines():
        if ":" in line:
            detail = line.split(":", 1)[1].strip()
            if detail and detail != "Not provided in Phase 0 intake.":
                return detail
    return ""


def _infer_topic_tags(question: str, intake_answers: tuple[IntakeAnswer, ...]) -> list[str]:
    text = " ".join([question, *[answer.answer for answer in intake_answers]]).lower()
    tags: list[str] = []
    for tag, keywords in {
        "business": ("company", "revenue", "arr", "sales", "hire", "hiring"),
        "people": ("team", "stakeholder", "employee", "family"),
        "strategy": ("strategy", "position", "market", "expansion"),
    }.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def _extract_section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    return match.group(1).strip()


def _summarize_consensus(positions: dict[str, str]) -> str:
    if not positions:
        return "No advisor outputs were available."
    return "\n".join(
        [
            "- Advisors completed the same structured contract in isolated contexts.",
            "- Each advisor grounded its position in the refined question and intake constraints.",
            "- The council should focus next on the fact or test that would change the recommendation.",
        ]
    )


def _summarize_tensions(positions: dict[str, str]) -> list[str]:
    if not positions:
        return ["- No tensions could be synthesized because no advisor outputs were available."]
    return [
        "- Optimist and Expander pressure-test the upside; Realist and Pre-mortem pressure-test cost and failure.",
        "- First-Principles asks whether the question is framed correctly; Stakeholder-Empathy asks how affected people experience the choice.",
        "- Researcher refuses fake certainty and asks which evidence would actually change the call.",
    ]


def _derive_crux(question: str) -> str:
    return (
        "The crux is whether the stated option solves the named bottleneck better "
        f"than a smaller reversible test of the same need: {question}"
    )


def _derive_follow_ups() -> list[str]:
    return [
        "- Ask Realist: what is the cheapest test before committing?",
        "- Ask Researcher: what evidence would reverse the recommendation?",
        "- Ask Stakeholder-Empathy: who bears the cost if the decision is wrong?",
    ]


def _so_what_sentence(intake_answers: tuple[IntakeAnswer, ...]) -> str:
    useful_change = intake_answers[2].answer
    if useful_change == "Not provided in Phase 0 intake.":
        return "Before acting, identify the cheapest concrete test that would change the decision."
    return f"Before acting, test whether the next step would actually deliver this change: {useful_change}"


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _council_date(council_id: str) -> str:
    raw = council_id[6:14]
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


if __name__ == "__main__":
    raise SystemExit(main())
