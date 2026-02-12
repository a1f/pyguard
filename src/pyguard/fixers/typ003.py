"""TYP003 fixer: Add type annotations for variables with inferable types."""
from __future__ import annotations

import ast
import tokenize
from tokenize import TokenInfo

from pyguard.fixers._util import apply_insertions, parse_source, tokenize_source

_BUILTIN_CONSTRUCTORS: frozenset[str] = frozenset({
    "int",
    "float",
    "str",
    "bytes",
    "bool",
    "complex",
    "list",
    "dict",
    "set",
    "frozenset",
    "tuple",
    "bytearray",
})


def fix_missing_variable_annotations(source: str) -> str:
    """Add type annotations to variables whose type is unambiguously inferable.

    Only fixes simple assignments where:
    - There is a single ``ast.Name`` target (no tuple unpack, attribute, subscript)
    - The target name is not ``_``
    - The assigned value is a literal with obvious type or a builtin constructor call
    """
    tree: ast.Module | None = parse_source(source)
    if tree is None:
        return source

    visitor: _FixableVisitor = _FixableVisitor()
    visitor.visit(tree)

    if not visitor.fixable:
        return source

    tokens: list[TokenInfo] = tokenize_source(source)
    if not tokens:
        return source

    insertions: list[tuple[int, int, str]] = []

    for node, type_name in visitor.fixable:
        target: ast.Name = node.targets[0]  # type: ignore[assignment]
        pos: tuple[int, int] | None = _find_name_token_end(
            tokens, name=target.id, line=target.lineno, col=target.col_offset,
        )
        if pos is not None:
            insertions.append((pos[0], pos[1], type_name))

    if not insertions:
        return source

    lines: list[str] = source.splitlines(keepends=True)
    for line_idx, col, type_name in sorted(insertions, reverse=True):
        line: str = lines[line_idx]
        lines[line_idx] = line[:col] + f": {type_name}" + line[col:]

    return apply_insertions(source, lines)


def _infer_type_annotation(node: ast.expr) -> str | None:
    """Return the type name if the value's type is unambiguously inferable.

    For ``ast.Call`` nodes this checks whether the callee name is in
    ``_BUILTIN_CONSTRUCTORS``.  No scope analysis is performed, so if a
    builtin name has been rebound (e.g. ``list = MyListFactory``) the
    inferred annotation may be incorrect.
    """
    if isinstance(node, ast.Constant):
        value: object = node.value
        # bool must be checked before int (bool is a subclass of int)
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, complex):
            return "complex"
        if isinstance(value, str):
            return "str"
        if isinstance(value, bytes):
            return "bytes"
        # Skip None and Ellipsis
        return None

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in _BUILTIN_CONSTRUCTORS:
            return node.func.id
        return None

    return None


class _FixableVisitor(ast.NodeVisitor):
    """Find assignments that can safely receive a type annotation."""

    def __init__(self) -> None:
        self.fixable: list[tuple[ast.Assign, str]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id != "_"
        ):
            type_name: str | None = _infer_type_annotation(node.value)
            if type_name is not None:
                self.fixable.append((node, type_name))
        self.generic_visit(node)


def _find_name_token_end(
    tokens: list[TokenInfo],
    *,
    name: str,
    line: int,
    col: int,
) -> tuple[int, int] | None:
    """Find the end position of a NAME token at the given AST location.

    Returns ``(line_0indexed, col)`` for the insertion point right after
    the name token.
    """
    for tok in tokens:
        if (
            tok.type == tokenize.NAME
            and tok.string == name
            and tok.start[0] == line
            and tok.start[1] == col
        ):
            return (tok.end[0] - 1, tok.end[1])
    return None
