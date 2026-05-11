#!/usr/bin/env python3
"""Validate the v1 advisor persona library and output contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PERSONAS = {
    "optimist.md": "Optimist",
    "realist.md": "Realist",
    "pre-mortem.md": "Pre-mortem",
    "expander.md": "Expander",
    "researcher.md": "Researcher",
    "devils-advocate.md": "Devil's Advocate",
    "first-principles.md": "First-Principles",
    "stakeholder-empathy.md": "Stakeholder-Empathy",
}

OUTPUT_SECTIONS = [
    "## Position",
    "## Key reasoning",
    "## What would change my view",
    "## Open questions for the room",
]

ANTI_SLOP_PHRASES = [
    "Every claim you make must be grounded in a specific detail from the question.",
    "If you find yourself writing something that would be true of any business decision, delete it.",
    "If you're tempted to hedge",
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def main() -> int:
    errors: list[str] = []

    personas_dir = ROOT / "personas"
    for filename, persona_name in PERSONAS.items():
        path = personas_dir / filename
        text = read(path)
        if not text:
            errors.append(f"missing persona: {path.relative_to(ROOT)}")
            continue

        if persona_name not in text:
            errors.append(f"{filename} does not name {persona_name}")

        for section in OUTPUT_SECTIONS:
            if section not in text:
                errors.append(f"{filename} missing output section {section!r}")

        for phrase in ANTI_SLOP_PHRASES:
            if phrase not in text:
                errors.append(f"{filename} missing anti-slop phrase {phrase!r}")

    contract = read(ROOT / "docs" / "advisor-output-contract.md")
    if not contract:
        errors.append("missing docs/advisor-output-contract.md")
    else:
        for section in OUTPUT_SECTIONS:
            if section not in contract:
                errors.append(f"advisor-output-contract.md missing {section!r}")
        for phrase in ANTI_SLOP_PHRASES:
            if phrase not in contract:
                errors.append(
                    f"advisor-output-contract.md missing anti-slop phrase {phrase!r}"
                )

    readme = read(personas_dir / "README.md")
    if not readme:
        errors.append("missing personas/README.md")
    elif "Ad-hoc persona format" not in readme:
        errors.append("personas/README.md missing ad-hoc persona format documentation")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Persona library contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
