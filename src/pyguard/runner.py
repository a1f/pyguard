"""Lint orchestrator for PyGuard."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyguard.constants import SYNTAX_ERROR_CODE, Severity
from pyguard.diagnostics import Diagnostic, DiagnosticCollection, SourceLocation
from pyguard.formatters import Formatter, format_summary, get_formatter
from pyguard.parser import ParseResult, SyntaxErrorInfo, parse_file
from pyguard.scanner import scan_files
from pyguard.types import PyGuardConfig


@dataclass(frozen=True, slots=True)
class LintResult:
    diagnostics: DiagnosticCollection
    files_checked: int
    exit_code: int


def _syntax_error_to_diagnostic(*, parse_result: ParseResult) -> Diagnostic:
    err: SyntaxErrorInfo | None = parse_result.syntax_error
    if err is None:
        raise ValueError("parse_result must have a syntax_error")
    return Diagnostic(
        file=parse_result.file,
        location=SourceLocation(line=err.line, column=err.column),
        code=SYNTAX_ERROR_CODE,
        message=err.message,
        severity=Severity.ERROR,
        source_line=err.source_line,
    )


def lint_paths(*, paths: tuple[Path, ...], config: PyGuardConfig) -> LintResult:
    files: list[Path] = scan_files(paths=paths, config=config)
    collection: DiagnosticCollection = DiagnosticCollection()

    for file in files:
        result: ParseResult = parse_file(file=file)
        if result.syntax_error is not None:
            collection.add(
                diagnostic=_syntax_error_to_diagnostic(parse_result=result),
            )

    exit_code: int = 1 if collection.has_errors else 0
    return LintResult(
        diagnostics=collection,
        files_checked=len(files),
        exit_code=exit_code,
    )


def format_results(*, result: LintResult, config: PyGuardConfig) -> str:
    formatter: Formatter = get_formatter(output_format=config.output_format)
    output: str = formatter.format(diagnostics=result.diagnostics, config=config)

    summary: str = format_summary(diagnostics=result.diagnostics)
    suffix: str = "s" if result.files_checked != 1 else ""
    file_count: str = f"Checked {result.files_checked} file{suffix}."

    parts: list[str] = []
    if output:
        parts.append(output)
    parts.append(summary)
    parts.append(file_count)

    return "\n".join(parts)
