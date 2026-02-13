"""KW001: Require keyword-only parameters."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import KW001Options, PyGuardConfig


class KW001Rule:
    """Detect functions that should use keyword-only parameters."""

    @property
    def code(self) -> str:
        return "KW001"

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
    """AST visitor that flags functions missing keyword-only parameter syntax."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("KW001")
        self._opts: KW001Options = config.rules.kw001
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

        if self._opts.exempt_private and _is_private(node.name):
            return

        if self._opts.exempt_overrides and _has_override_decorator(node):
            return

        # Already has keyword-only params or *args — no issue
        if node.args.kwonlyargs or node.args.vararg is not None:
            return

        is_method: bool = self._class_depth > 0
        positional_args: list[ast.arg] = list(node.args.args)

        # Strip self/cls from count for methods
        self_cls_offset: int = 0
        if is_method and positional_args and positional_args[0].arg in ("self", "cls"):
            self_cls_offset = 1

        effective_count: int = len(positional_args) - self_cls_offset
        if effective_count < self._opts.min_params:
            return

        kind: str = "Method" if is_method else "Function"
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
                code="KW001",
                message=f"{kind} '{node.name}' should use keyword-only parameters "
                "(add * separator)",
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def _is_private(name: str) -> bool:
    return name.startswith("_") and not _is_dunder(name)


def _has_override_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "override":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "override":
            return True
    return False
