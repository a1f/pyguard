"""Diagnostic data model for PyGuard."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pyguard.constants import Severity


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Source code location. All values are 1-based."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A single diagnostic (error, warning) found in code."""

    file: Path
    location: SourceLocation
    code: str
    message: str
    severity: Severity
    source_line: str | None = None


@dataclass(slots=True)
class DiagnosticCollection:
    """Mutable collection of diagnostics with sorting and counting."""

    _diagnostics: list[Diagnostic] = field(default_factory=list)

    def add(self, *, diagnostic: Diagnostic) -> None:
        """Add a single diagnostic."""
        self._diagnostics.append(diagnostic)

    def add_all(self, *, diagnostics: list[Diagnostic]) -> None:
        """Add multiple diagnostics."""
        self._diagnostics.extend(diagnostics)

    @property
    def sorted(self) -> list[Diagnostic]:
        """Return diagnostics sorted by file, line, column."""
        return sorted(
            self._diagnostics,
            key=lambda d: (str(d.file), d.location.line, d.location.column),
        )

    @property
    def has_errors(self) -> bool:
        """Return True if any diagnostic has ERROR severity."""
        return any(d.severity == Severity.ERROR for d in self._diagnostics)

    @property
    def error_count(self) -> int:
        """Count of ERROR severity diagnostics."""
        return sum(1 for d in self._diagnostics if d.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of WARN severity diagnostics."""
        return sum(1 for d in self._diagnostics if d.severity == Severity.WARN)

    def __len__(self) -> int:
        return len(self._diagnostics)

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self._diagnostics)
