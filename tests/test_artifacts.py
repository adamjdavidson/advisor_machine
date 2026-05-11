import sys
import tempfile
import unittest
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))

from advisor_machine.artifacts import (
    AdvisorOutput,
    CouncilArtifactLedger,
    CouncilRun,
    Memo,
    SynthOutput,
)


class CouncilArtifactLedgerTests(unittest.TestCase):
    def test_writes_council_artifact_layout_and_vault_memo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "beads"
            vault = Path(tmp) / "ADSB" / "Council"
            run = CouncilRun(
                council_id="am-123",
                date="2026-05-10",
                topic="coo-vs-engineer",
                tags=["business", "hiring"],
                refined_question="Should I hire a COO instead of another engineer?",
                constraints=["12 people", "$3M ARR", "sales and ops are eating shipping time"],
                intake_markdown="# Intake\n\nOriginal dump and clarifying Q&A.",
                lineup_markdown="# Lineup\n\n- Optimist: upside case\n- Realist: failure modes",
                advisor_outputs=[
                    AdvisorOutput(
                        round_number=1,
                        advisor_slug="optimist",
                        markdown="# Optimist\n\nA COO could unlock capacity.",
                    ),
                    AdvisorOutput(
                        round_number=1,
                        advisor_slug="realist",
                        markdown="# Realist\n\nThis can fail if the role is vague.",
                    ),
                    AdvisorOutput(
                        round_number=2,
                        advisor_slug="adhoc:founder-ceo",
                        markdown="# Founder CEO\n\nTest with a fractional operator first.",
                    ),
                ],
                synth_outputs=[
                    SynthOutput(
                        round_number=1,
                        markdown="# Synth Round 1\n\nThe crux is whether ops or product is the bottleneck.",
                        decision_markdown="# Decision\n\nRun round 2 for the founder CEO.",
                    ),
                    SynthOutput(
                        round_number=2,
                        markdown="# Synth Round 2\n\nThe cheapest test is a scoped 90-day engagement.",
                    ),
                ],
                memo=Memo(
                    title="Should I hire a COO instead of another engineer?",
                    body_markdown=(
                        "## TL;DR\n"
                        "Do not hire permanently before testing the role.\n\n"
                        "## The crux\n"
                        "Whether the bottleneck is operational drag or product capacity."
                    ),
                    verdict="sharpened",
                ),
            )

            result = CouncilArtifactLedger(root, vault).write_run(run)
            council_dir = root / "am-123"

            self.assertTrue(result.vault_written)
            self.assertIsNone(result.vault_error)
            self.assertEqual(council_dir, result.council_dir)
            self.assertEqual(council_dir / "99-memo.md", result.bead_memo_path)
            self.assertEqual(vault / "2026-05-10-coo-vs-engineer.md", result.vault_path)

            expected_files = [
                "00-intake.md",
                "01-question.md",
                "02-lineup.md",
                "advisors/round-1/optimist.md",
                "advisors/round-1/realist.md",
                "advisors/round-2/adhoc-founder-ceo.md",
                "synth/round-1.md",
                "synth/round-1-decision.md",
                "synth/round-2.md",
                "99-memo.md",
            ]
            for relative_path in expected_files:
                self.assertTrue((council_dir / relative_path).is_file(), relative_path)

            question = (council_dir / "01-question.md").read_text()
            self.assertIn("Should I hire a COO instead of another engineer?", question)
            self.assertIn("- $3M ARR", question)
            self.assertIn("- hiring", question)

            bead_memo = (council_dir / "99-memo.md").read_text()
            vault_memo = result.vault_path.read_text()
            self.assertEqual(bead_memo, vault_memo)
            self.assertIn("council: am-123", vault_memo)
            self.assertIn("date: 2026-05-10", vault_memo)
            self.assertIn("topic: coo-vs-engineer", vault_memo)
            self.assertIn("tags: [business, hiring]", vault_memo)
            self.assertIn("rounds: 2", vault_memo)
            self.assertIn("advisors: [optimist, realist, adhoc:founder-ceo]", vault_memo)
            self.assertIn("verdict: sharpened", vault_memo)
            self.assertIn("*Full transcript: bead am-123*", vault_memo)

    def test_vault_write_failure_preserves_bead_memo_and_reports_bead_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "beads"
            vault = Path(tmp) / "blocked-vault"
            vault.write_text("not a directory")
            run = CouncilRun(
                council_id="am-124",
                date="2026-05-11",
                topic="budget-choice",
                tags=["money"],
                refined_question="Which bet should I fund?",
                constraints=[],
                intake_markdown="intake",
                lineup_markdown="lineup",
                advisor_outputs=[],
                synth_outputs=[],
                memo=Memo(
                    title="Which bet should I fund?",
                    body_markdown="## TL;DR\nPick the one with a faster learning loop.",
                    verdict="resolved",
                ),
            )

            result = CouncilArtifactLedger(root, vault).write_run(run)

            self.assertFalse(result.vault_written)
            self.assertIsNotNone(result.vault_error)
            self.assertTrue(result.bead_memo_path.is_file())
            self.assertIn(str(result.bead_memo_path), result.report_message)
            self.assertIn("Vault write failed", result.report_message)


if __name__ == "__main__":
    unittest.main()
