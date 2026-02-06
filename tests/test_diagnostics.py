"""Tests for the diagnostics module."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, DiagnosticCollection, SourceLocation


class TestSourceLocation:
    """Tests for SourceLocation dataclass."""

    def test_creation_basic(self) -> None:
        """Create location with line and column only."""
        loc = SourceLocation(line=10, column=5)
        assert loc.line == 10
        assert loc.column == 5
        assert loc.end_line is None
        assert loc.end_column is None

    def test_creation_with_end(self) -> None:
        """Create location with end position."""
        loc = SourceLocation(line=10, column=5, end_line=12, end_column=20)
        assert loc.line == 10
        assert loc.column == 5
        assert loc.end_line == 12
        assert loc.end_column == 20

    def test_frozen(self) -> None:
        """SourceLocation is immutable."""
        loc = SourceLocation(line=1, column=1)
        with pytest.raises(FrozenInstanceError):
            loc.line = 2  # type: ignore[misc]


class TestDiagnostic:
    """Tests for Diagnostic dataclass."""

    def test_creation(self) -> None:
        """Create diagnostic with all fields."""
        loc = SourceLocation(line=3, column=5)
        diag = Diagnostic(
            file=Path("src/example.py"),
            location=loc,
            code="SYN001",
            message="Syntax error: expected ':'",
            severity=Severity.ERROR,
            source_line="def broken(",
        )
        assert diag.file == Path("src/example.py")
        assert diag.location.line == 3
        assert diag.code == "SYN001"
        assert diag.message == "Syntax error: expected ':'"
        assert diag.severity == Severity.ERROR
        assert diag.source_line == "def broken("

    def test_creation_without_source(self) -> None:
        """Create diagnostic without source line."""
        loc = SourceLocation(line=1, column=1)
        diag = Diagnostic(
            file=Path("test.py"),
            location=loc,
            code="TYP001",
            message="Missing annotation",
            severity=Severity.WARN,
        )
        assert diag.source_line is None

    def test_frozen(self) -> None:
        """Diagnostic is immutable."""
        loc = SourceLocation(line=1, column=1)
        diag = Diagnostic(
            file=Path("test.py"),
            location=loc,
            code="TYP001",
            message="test",
            severity=Severity.ERROR,
        )
        with pytest.raises(FrozenInstanceError):
            diag.message = "changed"  # type: ignore[misc]


class TestDiagnosticCollection:
    """Tests for DiagnosticCollection."""

    def _make_diagnostic(
        self,
        *,
        file: str = "test.py",
        line: int = 1,
        column: int = 1,
        code: str = "TST001",
        severity: Severity = Severity.ERROR,
    ) -> Diagnostic:
        """Helper to create diagnostics."""
        return Diagnostic(
            file=Path(file),
            location=SourceLocation(line=line, column=column),
            code=code,
            message="test message",
            severity=severity,
        )

    def test_add_single(self) -> None:
        """Add single diagnostic."""
        coll = DiagnosticCollection()
        diag = self._make_diagnostic()
        coll.add(diagnostic=diag)
        assert len(coll) == 1

    def test_add_all(self) -> None:
        """Add multiple diagnostics."""
        coll = DiagnosticCollection()
        diags = [
            self._make_diagnostic(line=1),
            self._make_diagnostic(line=2),
            self._make_diagnostic(line=3),
        ]
        coll.add_all(diagnostics=diags)
        assert len(coll) == 3

    def test_sorted_by_file_line_column(self) -> None:
        """Diagnostics sorted by file, line, column."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(file="b.py", line=10, column=5))
        coll.add(diagnostic=self._make_diagnostic(file="a.py", line=5, column=1))
        coll.add(diagnostic=self._make_diagnostic(file="a.py", line=5, column=10))
        coll.add(diagnostic=self._make_diagnostic(file="a.py", line=1, column=1))

        sorted_diags = coll.sorted
        assert str(sorted_diags[0].file) == "a.py"
        assert sorted_diags[0].location.line == 1
        assert str(sorted_diags[1].file) == "a.py"
        assert sorted_diags[1].location.line == 5
        assert sorted_diags[1].location.column == 1
        assert str(sorted_diags[2].file) == "a.py"
        assert sorted_diags[2].location.line == 5
        assert sorted_diags[2].location.column == 10
        assert str(sorted_diags[3].file) == "b.py"

    def test_has_errors_true(self) -> None:
        """has_errors returns True when ERROR present."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.WARN))
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.ERROR))
        assert coll.has_errors is True

    def test_has_errors_false(self) -> None:
        """has_errors returns False when no ERROR present."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.WARN))
        assert coll.has_errors is False

    def test_error_count(self) -> None:
        """error_count returns correct count."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.ERROR))
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.ERROR))
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.WARN))
        assert coll.error_count == 2

    def test_warning_count(self) -> None:
        """warning_count returns correct count."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.ERROR))
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.WARN))
        coll.add(diagnostic=self._make_diagnostic(severity=Severity.WARN))
        assert coll.warning_count == 2

    def test_empty_collection(self) -> None:
        """Empty collection behavior."""
        coll = DiagnosticCollection()
        assert len(coll) == 0
        assert coll.error_count == 0
        assert coll.warning_count == 0
        assert coll.has_errors is False
        assert coll.sorted == []

    def test_iteration(self) -> None:
        """Collection is iterable."""
        coll = DiagnosticCollection()
        coll.add(diagnostic=self._make_diagnostic(line=1))
        coll.add(diagnostic=self._make_diagnostic(line=2))
        lines = [d.location.line for d in coll]
        assert lines == [1, 2]
