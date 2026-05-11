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


if __name__ == "__main__":
    unittest.main()
