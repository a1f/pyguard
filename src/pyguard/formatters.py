"""Output formatters for PyGuard diagnostics."""
from __future__ import annotations

import json
from typing import Protocol

from pyguard.constants import OutputFormat
from pyguard.diagnostics import DiagnosticCollection
from pyguard.types import PyGuardConfig


class Formatter(Protocol):
    def format(
        self,
        *,
        diagnostics: DiagnosticCollection,
        config: PyGuardConfig,
    ) -> str: ...


class TextFormatter:
    def format(
        self,
        *,
        diagnostics: DiagnosticCollection,
        config: PyGuardConfig,
    ) -> str:
        lines: list[str] = []

        for diag in diagnostics.sorted:
            severity_str: str = diag.severity.value.upper()
            line: str = (
                f"{diag.file}:{diag.location.line}:{diag.location.column}: "
                f"{severity_str} [{diag.code}] {diag.message}"
            )
            lines.append(line)

            if config.show_source and diag.source_line is not None:
                lines.append(f"    {diag.source_line}")
                caret_pos: int = max(0, diag.location.column - 1)
                lines.append(f"    {' ' * caret_pos}^")
                lines.append("")

        return "\n".join(lines)


class JsonFormatter:
    def format(
        self,
        *,
        diagnostics: DiagnosticCollection,
        config: PyGuardConfig,
    ) -> str:
        items: list[dict[str, object]] = []

        for diag in diagnostics.sorted:
            item: dict[str, object] = {
                "file": str(diag.file),
                "line": diag.location.line,
                "column": diag.location.column,
                "end_line": diag.location.end_line,
                "end_column": diag.location.end_column,
                "code": diag.code,
                "severity": diag.severity.value,
                "message": diag.message,
            }
            if config.show_source:
                item["source_line"] = diag.source_line
            items.append(item)

        return json.dumps(items, indent=2)


def get_formatter(*, output_format: OutputFormat) -> Formatter:
    if output_format == OutputFormat.JSON:
        return JsonFormatter()
    if output_format == OutputFormat.GITHUB:
        raise NotImplementedError("GitHub annotation format is not yet implemented")
    return TextFormatter()


def format_summary(*, diagnostics: DiagnosticCollection) -> str:
    error_count: int = diagnostics.error_count
    warning_count: int = diagnostics.warning_count

    parts: list[str] = []
    if error_count > 0:
        parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
    if warning_count > 0:
        parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")

    if not parts:
        return "No issues found."

    return f"Found {', '.join(parts)}."
