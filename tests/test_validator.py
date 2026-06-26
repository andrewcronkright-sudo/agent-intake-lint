import unittest

from agent_intake_lint.config import DEFAULT_CONFIG, ValidationConfig
from agent_intake_lint.validator import validate_markdown


GOOD_NOTE = """---
type: observation
status: current
created_at: 2026-06-11T12:00:00Z
agent: codex
category: codex-workflow-and-automation
workstream: codex
source_paths:
  - /tmp/source.md
confidence: high
tags:
  - agent-intake
---
# Test Note

## Verdict
This note is valid.

## Evidence
- /tmp/source.md

## What Changed Or Was Learned
- A validator can catch drift.

## How Future Agents Should Use This
- Run the linter before committing notes.

## Follow-Up
- Done.
"""


class ValidatorTests(unittest.TestCase):
    def test_valid_note_passes(self):
        result = validate_markdown(GOOD_NOTE, "good.md")

        self.assertTrue(result.ok)
        self.assertEqual(result.issues, ())

    def test_missing_frontmatter_and_sections_fail(self):
        result = validate_markdown("# Bad\n\nNo metadata.", "bad.md")

        codes = {issue.code for issue in result.issues}
        self.assertIn("frontmatter.missing", codes)
        self.assertIn("body.heading", codes)

    def test_relative_source_path_fails(self):
        note = GOOD_NOTE.replace("/tmp/source.md", "relative/source.md", 1)

        result = validate_markdown(note, "relative.md")

        self.assertTrue(any(issue.code == "frontmatter.source_paths" for issue in result.issues))

    def test_suspected_secret_fails(self):
        note = GOOD_NOTE + "\napi_key = placeholder-value\n"

        result = validate_markdown(note, "secret.md")

        self.assertTrue(any(issue.code == "secret.suspected" for issue in result.issues))

    def test_empty_required_section_warns_without_failing(self):
        note = GOOD_NOTE.replace("## Follow-Up\n- Done.", "## Follow-Up\n")

        result = validate_markdown(note, "warning.md")

        self.assertTrue(result.ok)
        self.assertEqual(result.error_count, 0)
        self.assertTrue(any(issue.code == "body.empty_section" for issue in result.issues))

    def test_custom_config_can_allow_relative_source_paths(self):
        note = GOOD_NOTE.replace("/tmp/source.md", "docs/source.md")
        config = ValidationConfig(
            required_frontmatter=DEFAULT_CONFIG.required_frontmatter,
            allowed_types=DEFAULT_CONFIG.allowed_types,
            allowed_statuses=DEFAULT_CONFIG.allowed_statuses,
            allowed_confidence=DEFAULT_CONFIG.allowed_confidence,
            required_headings=DEFAULT_CONFIG.required_headings,
            allow_relative_source_paths=True,
        )

        result = validate_markdown(note, "relative.md", config=config)

        self.assertTrue(result.ok, result.issues)


if __name__ == "__main__":
    unittest.main()
