from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from agent_intake_lint.cli import main

from tests.test_validator import GOOD_NOTE


class CliTests(unittest.TestCase):
    def test_cli_validates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "note.md").write_text(GOOD_NOTE, encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(tmp_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("file(s) passed", stdout.getvalue())

    def test_cli_returns_failure_for_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.md"
            path.write_text("# Bad\n", encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([str(path)])

        self.assertEqual(exit_code, 1)
        self.assertIn("frontmatter.missing", stdout.getvalue())

    def test_strict_mode_fails_on_warning(self):
        warning_note = GOOD_NOTE.replace("## Follow-Up\n- Done.", "## Follow-Up\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "warning.md"
            path.write_text(warning_note, encoding="utf-8")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                normal_exit = main([str(path)])

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                strict_exit = main(["--strict", str(path)])

        self.assertEqual(normal_exit, 0)
        self.assertEqual(strict_exit, 1)
        self.assertIn("body.empty_section", stdout.getvalue())

    def test_init_config_writes_sample_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".agent-intake-lint.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                exit_code = main(["--init-config", str(path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue(path.exists())

    def test_custom_config_allows_team_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_path = tmp_path / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "required_frontmatter": ["type", "status", "created_at", "source_paths"],
                        "allowed": {"type": ["incident"], "status": ["current"], "confidence": ["high"]},
                        "required_headings": ["Verdict"],
                        "allow_relative_source_paths": True,
                    }
                ),
                encoding="utf-8",
            )
            note = tmp_path / "incident.md"
            note.write_text(
                "---\n"
                "type: incident\n"
                "status: current\n"
                "created_at: 2026-06-11T12:00:00Z\n"
                "source_paths:\n"
                "  - docs/source.md\n"
                "---\n"
                "# Incident\n\n"
                "## Verdict\n"
                "A team-specific contract can be linted.\n",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(["--config", str(config_path), str(note)])

        self.assertEqual(exit_code, 0)

    def test_baseline_suppresses_known_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            note = tmp_path / "bad.md"
            note.write_text("# Bad\n", encoding="utf-8")
            baseline = tmp_path / "baseline.json"

            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                write_exit = main(["--write-baseline", str(baseline), str(note)])
                lint_exit = main(["--baseline", str(baseline), str(note)])

        self.assertEqual(write_exit, 0)
        self.assertEqual(lint_exit, 0)

    def test_sarif_output_contains_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.md"
            path.write_text("# Bad\n", encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                exit_code = main(["--format", "sarif", str(path)])

        self.assertEqual(exit_code, 1)
        self.assertIn('"version": "2.1.0"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
