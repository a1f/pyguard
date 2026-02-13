"""EXP001: Structured return types must be module-level."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


class EXP001Rule:
    """Detect return types defined inside functions instead of at module level."""

    @property
    def code(self) -> str:
        return "EXP001"

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
    """AST visitor that flags class definitions inside functions used as return types."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("EXP001")
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
        return_name: str | None = _get_return_type_name(node.returns)
        if return_name is None:
            return

        for class_node in _find_classes_in_body(node):
            if class_node.name != return_name:
                continue
            # Use decorator line if present, otherwise class line
            line: int = (
                class_node.decorator_list[0].lineno
                if class_node.decorator_list
                else class_node.lineno
            )
            col: int = (
                class_node.decorator_list[0].col_offset + 1
                if class_node.decorator_list
                else class_node.col_offset + 1
            )
            source_line: str | None = None
            if 1 <= line <= len(self._source_lines):
                source_line = self._source_lines[line - 1]
            self.diagnostics.append(
                Diagnostic(
                    file=self._file,
                    location=SourceLocation(line=line, column=col),
                    code="EXP001",
                    message=f"Return type '{return_name}' should be defined "
                    "at module level for importability",
                    severity=self._severity,
                    source_line=source_line,
                ),
            )


def _get_return_type_name(annotation: ast.expr | None) -> str | None:
    """Extract a simple name from a return type annotation."""
    if annotation is None:
        return None
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    return None


def _find_classes_in_body(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.ClassDef]:
    """Find class definitions in a function body, excluding nested functions."""
    classes: list[ast.ClassDef] = []
    _collect_classes(node, classes)
    return classes


def _collect_classes(node: ast.AST, classes: list[ast.ClassDef]) -> None:
    """Recursively collect ClassDef nodes, skipping nested function definitions."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(child, ast.ClassDef):
            classes.append(child)
        _collect_classes(child, classes)
