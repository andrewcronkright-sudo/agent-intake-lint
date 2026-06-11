from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .validator import Issue, ValidationResult, validate_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate agent intake Markdown notes.")
    parser.add_argument("paths", nargs="+", help="Markdown files or directories to validate")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    files = list(_iter_markdown_files(args.paths))
    if not files:
        print("No Markdown files found.", file=sys.stderr)
        return 2

    results = [_validate_file(path) for path in files]

    if args.json:
        print(json.dumps([_result_to_json(result) for result in results], indent=2))
    else:
        _print_text(results)

    return 1 if any(not result.ok for result in results) else 0


def _iter_markdown_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if p.is_file()))
        elif path.is_file():
            files.append(path)
    return files


def _validate_file(path: Path) -> ValidationResult:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issue = Issue(str(path), 1, "file.encoding", "file is not valid UTF-8")
        return ValidationResult(str(path), (issue,))

    return validate_markdown(text, str(path))


def _print_text(results: list[ValidationResult]) -> None:
    issue_count = 0
    for result in results:
        if result.ok:
            print(f"OK {result.path}")
            continue

        for issue in result.issues:
            issue_count += 1
            print(f"{issue.path}:{issue.line}: {issue.code}: {issue.message}")

    if issue_count:
        print(f"\n{issue_count} issue(s) found.", file=sys.stderr)
    else:
        print(f"\n{len(results)} file(s) passed.")


def _result_to_json(result: ValidationResult) -> dict[str, object]:
    return {
        "path": result.path,
        "ok": result.ok,
        "issues": [
            {
                "line": issue.line,
                "code": issue.code,
                "message": issue.message,
            }
            for issue in result.issues
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
