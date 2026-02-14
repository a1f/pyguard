"""Tests for PyGuard output formatters."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyguard.constants import OutputFormat, Severity
from pyguard.diagnostics import Diagnostic, DiagnosticCollection, SourceLocation
from pyguard.formatters import (
    JsonFormatter,
    TextFormatter,
    format_summary,
    get_formatter,
)
from pyguard.types import PyGuardConfig


def _make_diagnostic(
    *,
    file: str = "src/example.py",
    line: int = 1,
    column: int = 1,
    code: str = "TYP001",
    message: str = "Missing type annotation",
    severity: Severity = Severity.ERROR,
    source_line: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        file=Path(file),
        location=SourceLocation(line=line, column=column),
        code=code,
        message=message,
        severity=severity,
        source_line=source_line,
    )


class TestTextFormatter:
    def test_single_diagnostic(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic())
        config: PyGuardConfig = PyGuardConfig(show_source=False)
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        assert "src/example.py:1:1: ERROR [TYP001] Missing type annotation" in result

    def test_multiple_diagnostics(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(line=5, code="TYP001"))
        collection.add(diagnostic=_make_diagnostic(line=10, code="KW001", severity=Severity.WARN))
        config: PyGuardConfig = PyGuardConfig(show_source=False)
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        assert "TYP001" in result
        assert "KW001" in result
        assert "ERROR" in result
        assert "WARN" in result

    def test_with_source_line(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(
            diagnostic=_make_diagnostic(
                line=3,
                column=5,
                source_line="def broken(",
            )
        )
        config: PyGuardConfig = PyGuardConfig(show_source=True)
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        assert "def broken(" in result
        assert "    ^" in result

    def test_without_source(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(
            diagnostic=_make_diagnostic(source_line="def foo():"),
        )
        config: PyGuardConfig = PyGuardConfig(show_source=False)
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        assert "def foo():" not in result

    def test_empty_collection(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        config: PyGuardConfig = PyGuardConfig()
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        assert result == ""

    def test_caret_at_column_1(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(
            diagnostic=_make_diagnostic(column=1, source_line="x = 1"),
        )
        config: PyGuardConfig = PyGuardConfig(show_source=True)
        result: str = TextFormatter().format(diagnostics=collection, config=config)
        lines: list[str] = result.split("\n")
        caret_line: str = [ln for ln in lines if "^" in ln][0]
        assert caret_line == "    ^"


class TestJsonFormatter:
    def test_single_diagnostic(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic())
        config: PyGuardConfig = PyGuardConfig()
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        data: list[dict[str, object]] = json.loads(result)
        assert len(data) == 1
        assert data[0]["file"] == "src/example.py"
        assert data[0]["code"] == "TYP001"
        assert data[0]["severity"] == "error"

    def test_multiple_diagnostics(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(code="TYP001"))
        collection.add(diagnostic=_make_diagnostic(line=5, code="KW001"))
        config: PyGuardConfig = PyGuardConfig()
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        data: list[dict[str, object]] = json.loads(result)
        assert len(data) == 2

    def test_null_end_positions(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic())
        config: PyGuardConfig = PyGuardConfig()
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        data: list[dict[str, object]] = json.loads(result)
        assert data[0]["end_line"] is None
        assert data[0]["end_column"] is None

    def test_source_line_included_when_show_source(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(source_line="x = 1"))
        config: PyGuardConfig = PyGuardConfig(show_source=True)
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        data: list[dict[str, object]] = json.loads(result)
        assert data[0]["source_line"] == "x = 1"

    def test_source_line_excluded_when_no_show_source(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(source_line="x = 1"))
        config: PyGuardConfig = PyGuardConfig(show_source=False)
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        data: list[dict[str, object]] = json.loads(result)
        assert "source_line" not in data[0]

    def test_empty_collection(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        config: PyGuardConfig = PyGuardConfig()
        result: str = JsonFormatter().format(diagnostics=collection, config=config)
        assert json.loads(result) == []


class TestGetFormatter:
    def test_text(self) -> None:
        formatter = get_formatter(output_format=OutputFormat.TEXT)
        assert isinstance(formatter, TextFormatter)

    def test_json(self) -> None:
        formatter = get_formatter(output_format=OutputFormat.JSON)
        assert isinstance(formatter, JsonFormatter)



class TestFormatSummary:
    def test_errors_only(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(severity=Severity.ERROR))
        assert format_summary(diagnostics=collection) == "Found 1 error."

    def test_warnings_only(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(severity=Severity.WARN))
        assert format_summary(diagnostics=collection) == "Found 1 warning."

    def test_mixed(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(severity=Severity.ERROR))
        collection.add(diagnostic=_make_diagnostic(severity=Severity.ERROR))
        collection.add(diagnostic=_make_diagnostic(severity=Severity.WARN))
        assert format_summary(diagnostics=collection) == "Found 2 errors, 1 warning."

    def test_empty(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        assert format_summary(diagnostics=collection) == "No issues found."

    def test_plural(self) -> None:
        collection: DiagnosticCollection = DiagnosticCollection()
        collection.add(diagnostic=_make_diagnostic(severity=Severity.WARN))
        collection.add(diagnostic=_make_diagnostic(severity=Severity.WARN))
        assert format_summary(diagnostics=collection) == "Found 2 warnings."
