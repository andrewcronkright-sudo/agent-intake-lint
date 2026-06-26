from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import DEFAULT_CONFIG_NAME, discover_config_path, load_config, write_sample_config
from .reporting import baseline_json, result_to_json, sarif_json
from .validator import Issue, ValidationResult, validate_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate agent intake Markdown notes.")
    parser.add_argument("paths", nargs="*", help="Markdown files or directories to validate")
    parser.add_argument("--baseline", help="ignore issues listed in a baseline JSON file")
    parser.add_argument("--config", help=f"path to config file; defaults to nearest {DEFAULT_CONFIG_NAME}")
    parser.add_argument("--format", choices=["text", "json", "sarif"], default="text", help="output format")
    parser.add_argument("--init-config", metavar="PATH", help="write a sample config file and exit")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument("--quiet", action="store_true", help="only print issues")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--write-baseline", metavar="PATH", help="write current issues as a baseline and exit 0")
    args = parser.parse_args(argv)

    if args.init_config:
        config_path = Path(args.init_config)
        write_sample_config(config_path)
        print(f"Wrote {config_path}")
        return 0

    if not args.paths:
        print("No paths provided.", file=sys.stderr)
        return 2

    try:
        config = _load_requested_config(args.config, args.paths)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    files = list(_iter_markdown_files(args.paths))
    if not files:
        print("No Markdown files found.", file=sys.stderr)
        return 2

    results = [_validate_file(path, config) for path in files]
    results = _apply_baseline(results, args.baseline)

    if args.write_baseline:
        Path(args.write_baseline).write_text(baseline_json(results), encoding="utf-8")
        print(f"Wrote {args.write_baseline}")
        return 0

    output_format = "json" if args.json else args.format
    if output_format == "json":
        print(json.dumps([result_to_json(result) for result in results], indent=2))
    elif output_format == "sarif":
        print(sarif_json(results))
    else:
        _print_text(results, quiet=args.quiet)

    has_errors = any(not result.ok for result in results)
    has_warnings = any(result.warning_count for result in results)
    return 1 if has_errors or (args.strict and has_warnings) else 0


def _iter_markdown_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if p.is_file()))
        elif path.is_file():
            files.append(path)
    return files


def _load_requested_config(raw_config: str | None, paths: list[str]):
    if raw_config:
        return load_config(Path(raw_config))

    first_path = Path(paths[0])
    return load_config(discover_config_path(first_path))


def _validate_file(path: Path, config) -> ValidationResult:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        issue = Issue(str(path), 1, "file.encoding", "file is not valid UTF-8")
        return ValidationResult(str(path), (issue,))

    return validate_markdown(text, str(path), config=config)


def _apply_baseline(results: list[ValidationResult], baseline_path: str | None) -> list[ValidationResult]:
    if not baseline_path:
        return results

    try:
        raw = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"{baseline_path}: could not read baseline: {exc}") from exc

    ignored = set(raw.get("fingerprints", [])) if isinstance(raw, dict) else set()
    return [
        ValidationResult(result.path, tuple(issue for issue in result.issues if issue.fingerprint not in ignored))
        for result in results
    ]


def _print_text(results: list[ValidationResult], quiet: bool = False) -> None:
    issue_count = 0
    warning_count = 0
    for result in results:
        if result.ok:
            if not quiet:
                if result.warning_count:
                    print(f"WARN {result.path} ({result.warning_count} warning(s))")
                else:
                    print(f"OK {result.path}")
            for issue in result.issues:
                if issue.severity != "error":
                    warning_count += 1
                    print(f"{issue.path}:{issue.line}: {issue.severity}: {issue.code}: {issue.message}")
            continue

        for issue in result.issues:
            if issue.severity == "error":
                issue_count += 1
            else:
                warning_count += 1
            print(f"{issue.path}:{issue.line}: {issue.severity}: {issue.code}: {issue.message}")

    if issue_count:
        print(f"\n{issue_count} error(s), {warning_count} warning(s) found.", file=sys.stderr)
    elif not quiet:
        print(f"\n{len(results)} file(s) passed with {warning_count} warning(s).")


if __name__ == "__main__":
    raise SystemExit(main())
