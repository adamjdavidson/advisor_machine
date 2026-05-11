import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"


class CouncilSkeletonTests(unittest.TestCase):
    def test_build_skeleton_creates_expected_artifact_layout(self) -> None:
        sys.path.insert(0, str(SRC_ROOT))
        from advisor_machine.council import build_council_skeleton

        fixed_now = datetime(2026, 5, 11, 9, 49, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skeleton = build_council_skeleton(
                "Should I hire a COO instead of another senior engineer?",
                state_dir=base / "state",
                vault_dir=base / "vault",
                now=fixed_now,
            )

            self.assertEqual(
                skeleton.council_dir.name,
                "draft-20260511-094900-should-i-hire-a-coo-instead-of-another-senior",
            )
            self.assertTrue((skeleton.council_dir / "00-intake.md").is_file())
            self.assertTrue((skeleton.council_dir / "01-question.md").is_file())
            self.assertTrue((skeleton.council_dir / "02-lineup.md").is_file())
            self.assertTrue((skeleton.council_dir / "advisors" / "round-1").is_dir())
            self.assertTrue((skeleton.council_dir / "synth").is_dir())
            self.assertTrue((skeleton.council_dir / "99-memo.md").is_file())
            self.assertEqual(
                skeleton.vault_path,
                base / "vault" / "2026-05-11-should-i-hire-a-coo-instead-of-another-senior.md",
            )

            intake = (skeleton.council_dir / "00-intake.md").read_text()
            self.assertIn("Should I hire a COO", intake)

    def test_cli_prints_skeleton_path_and_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(SRC_ROOT)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "advisor_machine.council",
                    "--state-dir",
                    str(base / "state"),
                    "--vault-dir",
                    str(base / "vault"),
                    "Should I hire a COO?",
                ],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Council skeleton ready", result.stdout)
            self.assertIn("Skeleton:", result.stdout)
            self.assertIn("99-memo.md", result.stdout)

            skeleton_line = next(
                line for line in result.stdout.splitlines() if line.startswith("Skeleton:")
            )
            skeleton_path = Path(skeleton_line.split(":", 1)[1].strip())
            self.assertTrue(skeleton_path.is_dir())

    def test_run_pipeline_writes_intake_advisors_synth_and_memo(self) -> None:
        sys.path.insert(0, str(SRC_ROOT))
        from advisor_machine.council import PERSONAS, run_council_pipeline

        fixed_now = datetime(2026, 5, 11, 10, 30, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = run_council_pipeline(
                "Should I hire a COO instead of another senior engineer?",
                answers=[
                    "I need a decision memo for a permanent leadership hire.",
                    "12 people, $3M ARR, mostly engineers, sales and ops eat my time.",
                    "A useful answer would show the cheapest test before hiring.",
                ],
                state_dir=base / "state",
                vault_dir=base / "vault",
                now=fixed_now,
            )

            intake = (run.skeleton.council_dir / "00-intake.md").read_text()
            self.assertIn("Q1. What decision or output", intake)
            self.assertIn("Q2. What context or constraints", intake)
            self.assertIn("Q3. What would a useful answer", intake)

            lineup = (run.skeleton.council_dir / "02-lineup.md").read_text()
            self.assertIn("Approval: approved", lineup)
            self.assertIn("Optimist (`optimist`)", lineup)

            for slug, _display in PERSONAS:
                advisor_output = run.skeleton.council_dir / "advisors" / "round-1" / f"{slug}.md"
                advisor_prompt = (
                    run.skeleton.council_dir
                    / "advisors"
                    / "round-1"
                    / "prompts"
                    / f"{slug}.prompt.md"
                )
                self.assertTrue(advisor_output.is_file(), advisor_output)
                self.assertTrue(advisor_prompt.is_file(), advisor_prompt)
                text = advisor_output.read_text()
                self.assertIn("## Position", text)
                self.assertIn("## Key reasoning", text)
                self.assertIn("## What would change my view", text)
                self.assertIn("## Open questions for the room", text)

            optimist_prompt = (
                run.skeleton.council_dir
                / "advisors"
                / "round-1"
                / "prompts"
                / "optimist.prompt.md"
            ).read_text()
            self.assertIn("# Optimist", optimist_prompt)
            self.assertNotIn("# Realist", optimist_prompt)

            synth = (run.skeleton.council_dir / "synth" / "round-1.md").read_text()
            self.assertIn("## Crux", synth)
            self.assertIn("## Consensus", synth)
            self.assertIn("## Tensions", synth)
            self.assertIn("## Proposed follow-ups", synth)

            memo = (run.skeleton.council_dir / "99-memo.md").read_text()
            self.assertIn("date: 2026-05-11", memo)
            self.assertIn("verdict: yellow sharpened", memo)
            self.assertIn('so_what: "Before acting, test whether', memo)
            self.assertIn("## So What Gate", memo)
            self.assertIn("## The crux", memo)
            self.assertEqual(run.vault_status, "written")
            self.assertTrue(run.skeleton.vault_path.is_file())

    def test_run_pipeline_retries_advisor_failures_once(self) -> None:
        sys.path.insert(0, str(SRC_ROOT))
        from advisor_machine.council import AdvisorTask, default_advisor_runner, run_council_pipeline

        attempts: dict[str, int] = {}

        def flaky_runner(task: AdvisorTask) -> str:
            attempts[task.slug] = attempts.get(task.slug, 0) + 1
            if task.slug == "realist" and attempts[task.slug] == 1:
                raise RuntimeError("temporary advisor failure")
            return default_advisor_runner(task)

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = run_council_pipeline(
                "Should I expand Feedforward expeditions?",
                answers=["Decision memo.", "Enterprise AI members.", "Pick next step."],
                state_dir=base / "state",
                vault_dir=base / "vault",
                now=datetime(2026, 5, 11, 11, 0, tzinfo=timezone.utc),
                advisor_runner=flaky_runner,
            )

            self.assertEqual(attempts["realist"], 2)
            self.assertTrue(
                (run.skeleton.council_dir / "advisors" / "round-1" / "realist.md").is_file()
            )
            retry_log = (
                run.skeleton.council_dir / "advisors" / "round-1" / "retry-policy.md"
            ).read_text()
            self.assertIn("Retry-on-advisor-failure: implemented", retry_log)
            self.assertIn("realist: attempt 1 failed", retry_log)


if __name__ == "__main__":
    unittest.main()
