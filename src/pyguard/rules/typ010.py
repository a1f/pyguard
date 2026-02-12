"""TYP010: Disallow legacy typing syntax."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig

_LEGACY_NAMES: frozenset[str] = frozenset({
    "Optional",
    "Union",
    "List",
    "Dict",
    "Tuple",
    "Set",
    "FrozenSet",
    "Type",
})

_BUILTIN_REPLACEMENTS: dict[str, str] = {
    "List": "list",
    "Dict": "dict",
    "Tuple": "tuple",
    "Set": "set",
    "FrozenSet": "frozenset",
    "Type": "type",
}


class TYP010Rule:
    """Detect legacy typing syntax that should use modern equivalents."""

    @property
    def code(self) -> str:
        return "TYP010"

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
    """AST visitor that collects legacy typing diagnostics."""

    def __init__(
        self,
        *,
        config: PyGuardConfig,
        file: Path,
        source_lines: tuple[str, ...],
    ) -> None:
        self._severity: Severity = config.get_severity("TYP010")
        self._file: Path = file
        self._source_lines: tuple[str, ...] = source_lines
        self._typing_imports: set[str] = set()
        self.diagnostics: list[Diagnostic] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "typing" and node.names:
            for alias in node.names:
                if alias.name in _LEGACY_NAMES:
                    self._typing_imports.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_annotation(node.annotation)
        self.generic_visit(node)

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        all_args: list[ast.arg] = [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]
        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)

        for arg in all_args:
            if arg.annotation is not None:
                self._check_annotation(arg.annotation)

        if node.returns is not None:
            self._check_annotation(node.returns)

    def _check_annotation(self, node: ast.expr) -> None:
        """Find outermost legacy typing nodes in an annotation and report them."""
        legacy_name: str | None = self._get_legacy_name(node)
        if legacy_name is not None:
            modern: str = _modernize(node, self._typing_imports)
            original: str = ast.unparse(node)
            self._add_diagnostic(
                node=node,
                message=f"Use '{modern}' instead of '{original}'",
            )
            return

        # Not a legacy node at top level — recurse into subscript slices
        if isinstance(node, ast.Subscript):
            self._check_annotation_in_slice(node.slice)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            self._check_annotation(node.left)
            self._check_annotation(node.right)

    def _check_annotation_in_slice(self, node: ast.expr) -> None:
        if isinstance(node, ast.Tuple):
            for elt in node.elts:
                self._check_annotation(elt)
        else:
            self._check_annotation(node)

    def _get_legacy_name(self, node: ast.expr) -> str | None:
        """Return the legacy typing name if node is a legacy typing subscript."""
        if not isinstance(node, ast.Subscript):
            return None

        value: ast.expr = node.value

        # from typing import List; List[str]
        if isinstance(value, ast.Name) and value.id in self._typing_imports:
            return value.id

        # import typing; typing.List[str]
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "typing"
            and value.attr in _LEGACY_NAMES
        ):
            return value.attr

        return None

    def _add_diagnostic(self, *, node: ast.expr, message: str) -> None:
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
                code="TYP010",
                message=message,
                severity=self._severity,
                source_line=source_line,
            ),
        )


def _modernize(node: ast.expr, typing_imports: set[str]) -> str:
    """Recursively produce the modern typing string for an annotation node."""
    legacy_name: str | None = _get_legacy_name_static(node, typing_imports)

    if legacy_name is not None and isinstance(node, ast.Subscript):
        if legacy_name == "Optional":
            inner: str = _modernize(node.slice, typing_imports)
            return f"{inner} | None"

        if legacy_name == "Union":
            if isinstance(node.slice, ast.Tuple):
                parts: list[str] = [
                    _modernize(e, typing_imports) for e in node.slice.elts
                ]
            else:
                parts = [_modernize(node.slice, typing_imports)]
            return " | ".join(parts)

        if legacy_name in _BUILTIN_REPLACEMENTS:
            replacement: str = _BUILTIN_REPLACEMENTS[legacy_name]
            inner_str: str = _modernize_slice(node.slice, typing_imports)
            return f"{replacement}[{inner_str}]"

    # Non-legacy subscript — still recurse into inner types
    if isinstance(node, ast.Subscript):
        value_str: str = ast.unparse(node.value)
        inner_str = _modernize_slice(node.slice, typing_imports)
        return f"{value_str}[{inner_str}]"

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left: str = _modernize(node.left, typing_imports)
        right: str = _modernize(node.right, typing_imports)
        return f"{left} | {right}"

    return ast.unparse(node)


def _modernize_slice(node: ast.expr, typing_imports: set[str]) -> str:
    """Modernize a subscript slice (may be a Tuple of elements)."""
    if isinstance(node, ast.Tuple):
        return ", ".join(_modernize(e, typing_imports) for e in node.elts)
    return _modernize(node, typing_imports)


def _get_legacy_name_static(
    node: ast.expr, typing_imports: set[str]
) -> str | None:
    """Return the legacy typing name if node is a legacy typing subscript."""
    if not isinstance(node, ast.Subscript):
        return None

    value: ast.expr = node.value

    if isinstance(value, ast.Name) and value.id in typing_imports:
        return value.id

    if (
        isinstance(value, ast.Attribute)
        and isinstance(value.value, ast.Name)
        and value.value.id == "typing"
        and value.attr in _LEGACY_NAMES
    ):
        return value.attr

    return None
