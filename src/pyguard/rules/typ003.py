"""TYP003: Missing variable type annotations."""
from __future__ import annotations

import ast
from enum import Enum
from pathlib import Path

from pyguard.constants import AnnotationScope, Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig, TYP003Options


class _Scope(Enum):
    """Tracks what scope the visitor is currently inside."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


_SCOPE_LABELS: dict[_Scope, str] = {
    _Scope.MODULE: "module-level",
    _Scope.CLASS: "class",
    _Scope.FUNCTION: "local",
}

_SCOPE_TO_ANNOTATION: dict[_Scope, AnnotationScope] = {
    _Scope.MODULE: AnnotationScope.MODULE,
    _Scope.CLASS: AnnotationScope.CLASS,
    _Scope.FUNCTION: AnnotationScope.LOCAL,
}


class TYP003Rule:
    """Detect variables missing type annotations."""

    @property
    def code(self) -> str:
        return "TYP003"

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
    """AST visitor that collects missing variable annotation diagnostics."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("TYP003")
        self._opts: TYP003Options = config.rules.typ003
        self._file: Path = file
        self._source_lines: tuple[str, ...] = source_lines
        self._scope_stack: list[_Scope] = [_Scope.MODULE]
        self.diagnostics: list[Diagnostic] = []

    @property
    def _current_scope(self) -> _Scope:
        return self._scope_stack[-1]

    def _scope_enabled(self) -> bool:
        annotation_scope: AnnotationScope = _SCOPE_TO_ANNOTATION[self._current_scope]
        return annotation_scope in self._opts.scope

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope_stack.append(_Scope.CLASS)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._scope_stack.append(_Scope.FUNCTION)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._scope_stack.append(_Scope.FUNCTION)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if not self._scope_enabled():
            self.generic_visit(node)
            return

        for target in node.targets:
            if isinstance(target, ast.Name) and not _is_exempt(target.id):
                self._add_diagnostic(name=target.id, lineno=target.lineno, col=target.col_offset)

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)

    def _add_diagnostic(self, *, name: str, lineno: int, col: int) -> None:
        label: str = _SCOPE_LABELS[self._current_scope]
        source_line: str | None = None
        if 1 <= lineno <= len(self._source_lines):
            source_line = self._source_lines[lineno - 1]

        self.diagnostics.append(
            Diagnostic(
                file=self._file,
                location=SourceLocation(line=lineno, column=col + 1),
                code="TYP003",
                message=f"Missing type annotation for {label} variable '{name}'",
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _is_exempt(name: str) -> bool:
    """Check if variable name is exempt from annotation requirement."""
    return name == "_"
