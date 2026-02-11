"""TYP001: Missing function parameter annotations."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig, TYP001Options


class TYP001Rule:
    """Detect function parameters missing type annotations."""

    @property
    def code(self) -> str:
        return "TYP001"

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
    """AST visitor that collects missing parameter annotation diagnostics."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("TYP001")
        self._opts: TYP001Options = config.rules.typ001
        self._file: Path = file
        self._source_lines: tuple[str, ...] = source_lines
        self._class_depth: int = 0
        self.diagnostics: list[Diagnostic] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        self.generic_visit(node)
        self._class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if self._opts.exempt_dunder and _is_dunder(node.name):
            return

        is_method: bool = self._class_depth > 0
        all_args: list[ast.arg] = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]

        for i, arg in enumerate(all_args):
            if is_method and self._opts.exempt_self_cls and i == 0 and arg.arg in ("self", "cls"):
                continue

            if arg.annotation is None:
                self._add_diagnostic(arg=arg)

    def _add_diagnostic(self, *, arg: ast.arg) -> None:
        source_line: str | None = None
        if 1 <= arg.lineno <= len(self._source_lines):
            source_line = self._source_lines[arg.lineno - 1]

        self.diagnostics.append(
            Diagnostic(
                file=self._file,
                location=SourceLocation(
                    line=arg.lineno,
                    column=arg.col_offset + 1,
                ),
                code="TYP001",
                message=f"Missing type annotation for parameter '{arg.arg}'",
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")
