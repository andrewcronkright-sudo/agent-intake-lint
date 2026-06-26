from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import PurePosixPath
from typing import Iterable

from .config import DEFAULT_CONFIG, ValidationConfig

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]+"), "credential assignment"),
    (re.compile(r"(?i)\b(cookie|sessionid|session_token)\s*[:=]"), "cookie or session value"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style API key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "GitHub-style token"),
]


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    code: str
    message: str
    severity: str = "error"

    @property
    def fingerprint(self) -> str:
        return f"{self.path}:{self.code}:{self.message}"


@dataclass(frozen=True)
class ValidationResult:
    path: str
    issues: tuple[Issue, ...]

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


def validate_markdown(
    text: str,
    path: str = "<memory>",
    config: ValidationConfig = DEFAULT_CONFIG,
) -> ValidationResult:
    issues: list[Issue] = []
    frontmatter, body, body_start_line = _split_frontmatter(text, path, issues)

    if frontmatter is not None:
        parsed = _parse_frontmatter(frontmatter, path, issues)
        _validate_frontmatter(parsed, path, issues, config)
    else:
        body = text
        body_start_line = 1

    _validate_body(body, body_start_line, path, issues, config)
    _scan_for_secrets(text, path, issues)

    return ValidationResult(path=path, issues=tuple(issues))


def _split_frontmatter(
    text: str, path: str, issues: list[Issue]
) -> tuple[str | None, str, int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        issues.append(Issue(path, 1, "frontmatter.missing", "missing opening frontmatter delimiter"))
        return None, text, 1

    for index, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            frontmatter = "\n".join(lines[1 : index - 1])
            body = "\n".join(lines[index:])
            return frontmatter, body, index + 1

    issues.append(Issue(path, 1, "frontmatter.unclosed", "missing closing frontmatter delimiter"))
    return None, text, 1


def _parse_frontmatter(frontmatter: str, path: str, issues: list[Issue]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    current_list_key: str | None = None

    for offset, raw_line in enumerate(frontmatter.splitlines(), start=2):
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        list_item = re.match(r"^\s*-\s+(.+?)\s*$", line)
        if list_item and current_list_key:
            parsed.setdefault(current_list_key, [])
            value = _strip_quotes(list_item.group(1).strip())
            current_value = parsed[current_list_key]
            if isinstance(current_value, list):
                current_value.append(value)
            continue

        if ":" not in line:
            issues.append(Issue(path, offset, "frontmatter.syntax", "expected key: value"))
            current_list_key = None
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            issues.append(Issue(path, offset, "frontmatter.syntax", "empty key"))
            current_list_key = None
            continue

        if value == "":
            parsed[key] = []
            current_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            parsed[key] = [
                _strip_quotes(item.strip())
                for item in value[1:-1].split(",")
                if item.strip()
            ]
            current_list_key = None
        else:
            parsed[key] = _strip_quotes(value)
            current_list_key = None

    return parsed


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _validate_frontmatter(
    parsed: dict[str, object],
    path: str,
    issues: list[Issue],
    config: ValidationConfig,
) -> None:
    missing = sorted(config.required_frontmatter.difference(parsed))
    for key in missing:
        issues.append(Issue(path, 1, "frontmatter.required", f"missing required field: {key}"))

    _check_allowed(parsed, "type", set(config.allowed_types), path, issues)
    _check_allowed(parsed, "status", set(config.allowed_statuses), path, issues)
    _check_allowed(parsed, "confidence", set(config.allowed_confidence), path, issues)

    created_at = parsed.get("created_at")
    if isinstance(created_at, str):
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            issues.append(Issue(path, 1, "frontmatter.created_at", "created_at must be ISO-8601"))

    source_paths = parsed.get("source_paths")
    if "source_paths" in config.required_frontmatter and (not isinstance(source_paths, list) or not source_paths):
        issues.append(Issue(path, 1, "frontmatter.source_paths", "source_paths must be a non-empty list"))
    elif isinstance(source_paths, list):
        for source_path in source_paths:
            if (
                not isinstance(source_path, str)
                or (not config.allow_relative_source_paths and not PurePosixPath(source_path).is_absolute())
            ):
                issues.append(
                    Issue(path, 1, "frontmatter.source_paths", f"source path is not absolute: {source_path}")
                )

    tags = parsed.get("tags")
    if "tags" in config.required_frontmatter and (not isinstance(tags, list) or not tags):
        issues.append(Issue(path, 1, "frontmatter.tags", "tags must be a non-empty list"))


def _check_allowed(
    parsed: dict[str, object],
    key: str,
    allowed: set[str],
    path: str,
    issues: list[Issue],
) -> None:
    value = parsed.get(key)
    if isinstance(value, str) and value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        issues.append(Issue(path, 1, f"frontmatter.{key}", f"{key} must be one of: {allowed_values}"))


def _validate_body(
    body: str,
    body_start_line: int,
    path: str,
    issues: list[Issue],
    config: ValidationConfig,
) -> None:
    sections = _collect_sections(body)
    headings = set(sections)
    for heading in config.required_headings:
        if heading not in headings:
            issues.append(Issue(path, body_start_line, "body.heading", f"missing section: {heading}"))
        elif not sections[heading]:
            issues.append(
                Issue(path, body_start_line, "body.empty_section", f"section has no body: {heading}", "warning")
            )


def _iter_headings(body: str) -> Iterable[str]:
    for line in body.splitlines():
        match = re.match(r"^#{2,6}\s+(.+?)\s*$", line)
        if match:
            yield match.group(1).strip()


def _collect_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in body.splitlines():
        match = re.match(r"^#{2,6}\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)

    return {heading: "\n".join(lines).strip() for heading, lines in sections.items()}


def _scan_for_secrets(text: str, path: str, issues: list[Issue]) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(line):
                issues.append(Issue(path, line_number, "secret.suspected", f"suspected {label}"))
