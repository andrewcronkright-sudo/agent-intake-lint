from __future__ import annotations

from collections.abc import Iterable
import json

from .validator import Issue, ValidationResult


def issue_to_json(issue: Issue) -> dict[str, object]:
    return {
        "line": issue.line,
        "severity": issue.severity,
        "code": issue.code,
        "message": issue.message,
        "fingerprint": issue.fingerprint,
    }


def result_to_json(result: ValidationResult) -> dict[str, object]:
    return {
        "path": result.path,
        "ok": result.ok,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "issues": [issue_to_json(issue) for issue in result.issues],
    }


def baseline_json(results: Iterable[ValidationResult]) -> str:
    fingerprints = sorted({issue.fingerprint for result in results for issue in result.issues})
    return json.dumps({"version": 1, "fingerprints": fingerprints}, indent=2) + "\n"


def sarif_json(results: Iterable[ValidationResult]) -> str:
    rules: dict[str, dict[str, object]] = {}
    sarif_results: list[dict[str, object]] = []

    for result in results:
        for issue in result.issues:
            rules.setdefault(
                issue.code,
                {
                    "id": issue.code,
                    "name": issue.code,
                    "shortDescription": {"text": issue.code},
                    "helpUri": "https://github.com/andrewcronkright-sudo/agent-intake-lint",
                },
            )
            sarif_results.append(
                {
                    "ruleId": issue.code,
                    "level": "error" if issue.severity == "error" else "warning",
                    "message": {"text": issue.message},
                    "fingerprints": {"agentIntakeLint": issue.fingerprint},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": issue.path},
                                "region": {"startLine": issue.line},
                            }
                        }
                    ],
                }
            )

    return json.dumps(
        {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "agent-intake-lint",
                            "informationUri": "https://github.com/andrewcronkright-sudo/agent-intake-lint",
                            "rules": list(rules.values()),
                        }
                    },
                    "results": sarif_results,
                }
            ],
        },
        indent=2,
    )
