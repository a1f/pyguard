"""TYP002 fixer: Add -> None to functions that don't return a value."""
from __future__ import annotations

import ast
import io
import tokenize
from tokenize import TokenInfo


def fix_missing_return_none(source: str) -> str:
    """Add ``-> None`` annotation to functions that implicitly return None.

    Only fixes functions where:
    - No return annotation exists
    - No return statements with values exist
    - Function is not a generator (no yield / yield from)
    - Function is not a dunder method
    """
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return source

    visitor: _FixableVisitor = _FixableVisitor()
    visitor.visit(tree)

    if not visitor.fixable:
        return source

    tokens: list[TokenInfo] = _tokenize_source(source)
    insertions: list[tuple[int, int]] = []

    for node in visitor.fixable:
        pos: tuple[int, int] | None = _find_def_colon(tokens, node=node)
        if pos is not None:
            insertions.append(pos)

    if not insertions:
        return source

    lines: list[str] = source.splitlines(keepends=True)
    for line_idx, col in sorted(insertions, reverse=True):
        line: str = lines[line_idx]
        lines[line_idx] = line[:col] + " -> None" + line[col:]

    return "".join(lines)


def _tokenize_source(source: str) -> list[TokenInfo]:
    """Tokenize source code, returning empty list on error."""
    try:
        return list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return []


class _FixableVisitor(ast.NodeVisitor):
    """Find functions that can safely receive ``-> None`` annotation."""

    def __init__(self) -> None:
        self.fixable: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if _is_fixable(node):
            self.fixable.append(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if _is_fixable(node):
            self.fixable.append(node)
        self.generic_visit(node)


def _is_fixable(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function can safely get ``-> None`` annotation."""
    if node.returns is not None:
        return False
    if _is_dunder(node.name):
        return False
    scanner: _BodyScanner = _BodyScanner()
    for stmt in node.body:
        scanner.visit(stmt)
    return not scanner.has_return_value and not scanner.has_yield


def _is_dunder(name: str) -> bool:
    """Check if a name is a dunder method."""
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


class _BodyScanner(ast.NodeVisitor):
    """Scan function body for return values and yields.

    Skips nested function definitions to avoid false positives.
    """

    def __init__(self) -> None:
        self.has_return_value: bool = False
        self.has_yield: bool = False

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is not None:
            self.has_return_value = True

    def visit_Yield(self, node: ast.Yield) -> None:
        self.has_yield = True

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self.has_yield = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass


def _find_def_colon(
    tokens: list[TokenInfo],
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[int, int] | None:
    """Find the ``(line_0indexed, col)`` of the colon ending a def statement."""
    func_line: int = node.lineno
    body_line: int = node.body[0].lineno

    for i, tok in enumerate(tokens):
        if (
            tok.type == tokenize.NAME
            and tok.string == "def"
            and func_line <= tok.start[0] <= body_line
            and i + 1 < len(tokens)
            and tokens[i + 1].string == node.name
        ):
            return _find_colon_after(tokens, start=i + 2)

    return None


def _find_colon_after(
    tokens: list[TokenInfo],
    *,
    start: int,
) -> tuple[int, int] | None:
    """Find the first colon at bracket depth 0 starting from token index."""
    depth: int = 0
    for j in range(start, len(tokens)):
        t: TokenInfo = tokens[j]
        if t.type == tokenize.OP and t.string in ("(", "["):
            depth += 1
        elif t.type == tokenize.OP and t.string in (")", "]"):
            depth -= 1
        elif t.type == tokenize.OP and t.string == ":" and depth == 0:
            return (t.start[0] - 1, t.start[1])
    return None
