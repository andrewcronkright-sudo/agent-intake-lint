# Agent Intake Lint

Validate Markdown handoff notes that agents write for shared-memory systems.

This project is for teams that ask coding agents to leave durable notes after a
run: what changed, what evidence supports it, what future agents should check,
and what remains blocked. It catches missing frontmatter, weak source trails,
missing body sections, and obvious secret leaks before notes are committed.

## Why this exists

Agent handoffs are easy to write and hard to trust. A useful note needs enough
structure to be searchable later, but the structure should stay simple enough
that humans can still read it in a normal Markdown vault.

`agent-intake-lint` checks for:

- YAML-style frontmatter with required fields.
- Absolute source paths in `source_paths`.
- Required body sections such as `Verdict`, `Evidence`, and `Follow-Up`.
- Empty required sections, reported as warnings by default.
- Common secret patterns such as private keys, API key assignments, cookies, and
  token-like values.
- Team-specific note contracts from `.agent-intake-lint.json`.
- Baseline files for adopting the linter in existing note archives.
- SARIF output for GitHub code scanning and other CI systems.

It does not send files anywhere and does not need network access.

## Install

```bash
python -m pip install .
```

For local development:

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## Usage

Validate one file:

```bash
agent-intake-lint examples/good-intake.md
```

Validate a directory recursively:

```bash
agent-intake-lint path/to/intake-notes
```

Emit machine-readable output:

```bash
agent-intake-lint --json path/to/intake-notes
```

Emit SARIF for CI annotations:

```bash
agent-intake-lint --format sarif path/to/intake-notes > agent-intake-lint.sarif
```

Fail CI on warnings as well as errors:

```bash
agent-intake-lint --strict path/to/intake-notes
```

Only print diagnostics:

```bash
agent-intake-lint --quiet path/to/intake-notes
```

Create a starter config:

```bash
agent-intake-lint --init-config .agent-intake-lint.json
```

Adopt the linter in an existing archive without fixing every old note first:

```bash
agent-intake-lint --write-baseline .agent-intake-baseline.json notes/
agent-intake-lint --baseline .agent-intake-baseline.json notes/
```

## Configuration

The CLI automatically discovers the nearest `.agent-intake-lint.json` from the
first path being validated. Use `--config path/to/config.json` to pin a specific
contract.

```json
{
  "required_frontmatter": ["type", "status", "created_at", "source_paths"],
  "allowed": {
    "type": ["decision", "handoff", "incident", "observation"],
    "status": ["current", "draft", "superseded"],
    "confidence": ["high", "medium", "low"]
  },
  "required_headings": ["Verdict", "Evidence", "Follow-Up"],
  "allow_relative_source_paths": true
}
```

This lets each team preserve its own durable-memory contract while still using
the same offline validator.

## Exit Codes

- `0`: no errors were found.
- `1`: one or more errors were found, or warnings were found with `--strict`.
- `2`: no Markdown files were found.

## Project Status

This is an offline-first validator for teams experimenting with durable agent
handoff notes. It is intentionally small enough to audit, but supports the
maintenance features a real shared-memory archive needs: custom contracts,
incremental adoption through baselines, CI output, and secret-leak checks. Rule
requests and bug reports are welcome through GitHub issues.

## Expected note shape

```markdown
---
type: observation
status: current
created_at: 2026-06-11T12:00:00Z
agent: codex
category: codex-workflow-and-automation
workstream: codex
source_paths:
  - /absolute/path/to/source.md
confidence: high
tags:
  - agent-intake
---

# Short Title

## Verdict
What is now true.

## Evidence
- /absolute/path/to/source.md

## What Changed Or Was Learned
- Durable point.

## How Future Agents Should Use This
- What to check first.

## Follow-Up
- Done, blocked, or next action.
```

## License

MIT
