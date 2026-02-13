"""IMP001: Disallow imports inside function bodies."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


class IMP001Rule:
    """Detect imports inside function bodies."""

    @property
    def code(self) -> str:
        return "IMP001"

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
    """AST visitor that flags imports inside function bodies."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("IMP001")
        self._file: Path = file
        self._source_lines: tuple[str, ...] = source_lines
        self._function_depth: int = 0
        self._in_type_checking: bool = False
        self._in_try_except_import: bool = False
        self.diagnostics: list[Diagnostic] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            prev: bool = self._in_type_checking
            self._in_type_checking = True
            for child in node.body:
                self.visit(child)
            self._in_type_checking = prev
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        if any(_catches_import_error(h) for h in node.handlers):
            prev: bool = self._in_try_except_import
            self._in_try_except_import = True
            self.generic_visit(node)
            self._in_try_except_import = prev
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if not self._should_flag():
            return
        for alias in node.names:
            self._add_diagnostic(node=node, module_name=alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not self._should_flag():
            return
        module: str = node.module or ""
        for alias in node.names:
            name: str = f"{module}.{alias.name}" if module else alias.name
            self._add_diagnostic(node=node, module_name=name)

    def _should_flag(self) -> bool:
        return (
            self._function_depth > 0
            and not self._in_type_checking
            and not self._in_try_except_import
        )

    def _add_diagnostic(
        self,
        *,
        node: ast.Import | ast.ImportFrom,
        module_name: str,
    ) -> None:
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
                code="IMP001",
                message=f"Import '{module_name}' should be at module level, "
                "not inside function",
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _is_type_checking_guard(test: ast.expr) -> bool:
    """Check if an expression is ``TYPE_CHECKING``."""
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return (
        isinstance(test, ast.Attribute)
        and isinstance(test.value, ast.Name)
        and test.attr == "TYPE_CHECKING"
    )


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    """Check if an except handler catches ImportError or ModuleNotFoundError."""
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in (
        "ImportError",
        "ModuleNotFoundError",
    ):
        return True
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(elt, ast.Name)
            and elt.id in ("ImportError", "ModuleNotFoundError")
            for elt in handler.type.elts
        )
    return False
