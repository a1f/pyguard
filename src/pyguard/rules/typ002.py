"""TYP002: Missing function return annotations."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


class TYP002Rule:
    """Detect functions missing return type annotations."""

    @property
    def code(self) -> str:
        return "TYP002"

    def check(
        self,
        *,
        parse_result: ParseResult,
        config: PyGuardConfig,
    ) -> list[Diagnostic]:
        if parse_result.tree is None:
            return []
        visitor: _Visitor = _Visitor(
            config=config,
            file=parse_result.file,
            source_lines=parse_result.source_lines,
        )
        visitor.visit(parse_result.tree)
        return visitor.diagnostics


class _Visitor(ast.NodeVisitor):
    """AST visitor that collects missing return annotation diagnostics."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("TYP002")
        self._file: Path = file
        self._source_lines: tuple[str, ...] = source_lines
        self.diagnostics: list[Diagnostic] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if _is_dunder(node.name):
            return

        if node.returns is not None:
            return

        source_line: str | None = None
        if 1 <= node.lineno <= len(self._source_lines):
            source_line = self._source_lines[node.lineno - 1]

        self.diagnostics.append(
            Diagnostic(
                file=self._file,
                location=SourceLocation(
                    line=node.lineno,
                    column=node.col_offset + 1,
                ),
                code="TYP002",
                message=f"Missing return type annotation for function '{node.name}'",
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")
