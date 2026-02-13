"""RET001: Disallow heterogeneous tuple returns."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


class RET001Rule:
    """Detect functions with heterogeneous tuple return types."""

    @property
    def code(self) -> str:
        return "RET001"

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
    """AST visitor that flags returns in functions with heterogeneous tuple annotations."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("RET001")
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
        if not _has_heterogeneous_tuple_annotation(node.returns):
            return

        for return_node in _find_return_statements(node):
            if return_node.value is None:
                continue
            source_line: str | None = None
            if 1 <= return_node.lineno <= len(self._source_lines):
                source_line = self._source_lines[return_node.lineno - 1]
            self.diagnostics.append(
                Diagnostic(
                    file=self._file,
                    location=SourceLocation(
                        line=return_node.lineno,
                        column=return_node.col_offset + 1,
                    ),
                    code="RET001",
                    message="Avoid tuple packing for return values; "
                    "use a dataclass or NamedTuple",
                    severity=self._severity,
                    source_line=source_line,
                ),
            )


def _has_heterogeneous_tuple_annotation(annotation: ast.expr | None) -> bool:
    """Check if a return annotation is a heterogeneous (fixed-length) tuple type."""
    if annotation is None:
        return False

    if not isinstance(annotation, ast.Subscript):
        return False

    # Check the base is 'tuple'
    if isinstance(annotation.value, ast.Name):
        if annotation.value.id != "tuple":
            return False
    elif isinstance(annotation.value, ast.Attribute):
        if annotation.value.attr != "tuple":
            return False
    else:
        return False

    # The slice must be a Tuple node with multiple elements
    slice_node: ast.expr = annotation.slice
    if not isinstance(slice_node, ast.Tuple):
        return False

    if len(slice_node.elts) < 2:
        return False

    # Exclude variadic form: tuple[T, ...]
    return not (
        len(slice_node.elts) == 2
        and isinstance(slice_node.elts[1], ast.Constant)
        and slice_node.elts[1].value is Ellipsis
    )


def _find_return_statements(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Return]:
    """Find return statements in a function body, excluding nested functions."""
    returns: list[ast.Return] = []
    _collect_returns(node, returns)
    return returns


def _collect_returns(node: ast.AST, returns: list[ast.Return]) -> None:
    """Recursively collect Return nodes, skipping nested function definitions."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(child, ast.Return):
            returns.append(child)
        _collect_returns(child, returns)
