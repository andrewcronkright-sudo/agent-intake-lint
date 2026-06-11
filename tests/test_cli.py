from contextlib import redirect_stderr, redirect_stdout
import io
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


if __name__ == "__main__":
    unittest.main()
