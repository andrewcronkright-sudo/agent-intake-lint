from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_NAME = ".agent-intake-lint.json"


@dataclass(frozen=True)
class ValidationConfig:
    required_frontmatter: frozenset[str]
    allowed_types: frozenset[str]
    allowed_statuses: frozenset[str]
    allowed_confidence: frozenset[str]
    required_headings: tuple[str, ...]
    allow_relative_source_paths: bool = False


DEFAULT_CONFIG = ValidationConfig(
    required_frontmatter=frozenset(
        {
            "type",
            "status",
            "created_at",
            "agent",
            "category",
            "workstream",
            "source_paths",
            "confidence",
            "tags",
        }
    ),
    allowed_types=frozenset(
        {
            "observation",
            "learning",
            "decision",
            "runbook",
            "source_map",
            "status",
            "handoff",
            "correction",
        }
    ),
    allowed_statuses=frozenset({"current", "draft", "stale", "superseded"}),
    allowed_confidence=frozenset({"high", "medium", "low"}),
    required_headings=(
        "Verdict",
        "Evidence",
        "What Changed Or Was Learned",
        "How Future Agents Should Use This",
        "Follow-Up",
    ),
)


SAMPLE_CONFIG = {
    "required_frontmatter": sorted(DEFAULT_CONFIG.required_frontmatter),
    "allowed": {
        "type": sorted(DEFAULT_CONFIG.allowed_types),
        "status": sorted(DEFAULT_CONFIG.allowed_statuses),
        "confidence": sorted(DEFAULT_CONFIG.allowed_confidence),
    },
    "required_headings": list(DEFAULT_CONFIG.required_headings),
    "allow_relative_source_paths": False,
}


def discover_config_path(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        candidate = directory / DEFAULT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | None) -> ValidationConfig:
    if path is None:
        return DEFAULT_CONFIG

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON config: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"{path}: config must be a JSON object")

    config = DEFAULT_CONFIG

    if "required_frontmatter" in raw:
        config = replace(
            config,
            required_frontmatter=frozenset(_string_list(raw["required_frontmatter"], "required_frontmatter")),
        )

    allowed = raw.get("allowed")
    if allowed is not None:
        if not isinstance(allowed, dict):
            raise ValueError(f"{path}: allowed must be an object")
        updates: dict[str, Any] = {}
        if "type" in allowed:
            updates["allowed_types"] = frozenset(_string_list(allowed["type"], "allowed.type"))
        if "status" in allowed:
            updates["allowed_statuses"] = frozenset(_string_list(allowed["status"], "allowed.status"))
        if "confidence" in allowed:
            updates["allowed_confidence"] = frozenset(_string_list(allowed["confidence"], "allowed.confidence"))
        config = replace(config, **updates)

    if "required_headings" in raw:
        config = replace(config, required_headings=tuple(_string_list(raw["required_headings"], "required_headings")))

    if "allow_relative_source_paths" in raw:
        value = raw["allow_relative_source_paths"]
        if not isinstance(value, bool):
            raise ValueError(f"{path}: allow_relative_source_paths must be true or false")
        config = replace(config, allow_relative_source_paths=value)

    return config


def write_sample_config(path: Path) -> None:
    path.write_text(json.dumps(SAMPLE_CONFIG, indent=2) + "\n", encoding="utf-8")


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return value
