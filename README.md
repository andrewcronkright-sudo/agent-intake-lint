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
- Common secret patterns such as private keys, API key assignments, cookies, and
  token-like values.

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
