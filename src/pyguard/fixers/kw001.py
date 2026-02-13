"""KW001 fixer: Insert * separator and rewrite call sites."""
from __future__ import annotations

import ast
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from tokenize import TokenInfo

from pyguard.fixers._util import parse_source, tokenize_source
from pyguard.types import KW001Options, PyGuardConfig


@dataclass(frozen=True, slots=True)
class CallSiteWarning:
    """Warning for a call site that could not be automatically rewritten."""

    file: Path
    line: int
    function_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class FixResult:
    """Result of applying KW001 fixes across a project."""

    sources: dict[Path, str]
    warnings: list[CallSiteWarning] = field(
        default_factory=lambda: list[CallSiteWarning]()
    )


def fix_keyword_only(
    *,
    sources: dict[Path, str],
    config: PyGuardConfig,
) -> FixResult:
    """
    Fix KW001: insert * separator and rewrite call sites.

    Phase 1: Insert ``*`` in function signatures.
    Phase 2: Rewrite call sites (not yet implemented).
    """
    opts: KW001Options = config.rules.kw001
    fixed_sources: dict[Path, str] = {}

    for file_path, source in sources.items():
        fixed: str = _fix_signatures(source, opts=opts)
        fixed_sources[file_path] = fixed

    return FixResult(sources=fixed_sources)


def _fix_signatures(source: str, *, opts: KW001Options) -> str:
    """Insert ``*, `` in function signatures that need keyword-only params."""
    tree: ast.Module | None = parse_source(source)
    if tree is None:
        return source

    visitor: _FixableVisitor = _FixableVisitor(opts=opts)
    visitor.visit(tree)

    if not visitor.fixable:
        return source

    tokens: list[TokenInfo] = tokenize_source(source)
    if not tokens:
        return source

    insertions: list[tuple[int, int, str]] = []

    for func_node in visitor.fixable:
        insertion: tuple[int, int, str] | None = _find_star_insertion(
            tokens, node=func_node,
        )
        if insertion is not None:
            insertions.append(insertion)

    if not insertions:
        return source

    lines: list[str] = source.splitlines(keepends=True)
    for line_idx, col, text in sorted(insertions, reverse=True):
        original_line: str = lines[line_idx]
        lines[line_idx] = original_line[:col] + text + original_line[col:]

    modified: str = "".join(lines)
    if parse_source(modified) is None:
        return source
    return modified


class _FixableVisitor(ast.NodeVisitor):
    """Find functions that need a ``*`` separator inserted."""

    def __init__(self, *, opts: KW001Options) -> None:
        self._opts: KW001Options = opts
        self._class_depth: int = 0
        self.fixable: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_depth += 1
        self.generic_visit(node)
        self._class_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._is_fixable(node):
            self.fixable.append(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._is_fixable(node):
            self.fixable.append(node)
        self.generic_visit(node)

    def _is_fixable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if self._opts.exempt_dunder and _is_dunder(node.name):
            return False
        if self._opts.exempt_private and _is_private(node.name):
            return False
        if self._opts.exempt_overrides and _has_override_decorator(node):
            return False
        if node.args.kwonlyargs or node.args.vararg is not None:
            return False

        is_method: bool = self._class_depth > 0
        positional: list[ast.arg] = list(node.args.args)
        self_cls_offset: int = 0
        if is_method and positional and positional[0].arg in ("self", "cls"):
            self_cls_offset = 1

        return len(positional) - self_cls_offset >= self._opts.min_params


def _find_star_insertion(
    tokens: list[TokenInfo],
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[int, int, str] | None:
    """
    Find where to insert ``*, `` in a function's parameter list.

    Returns ``(line_0indexed, col, text_to_insert)`` or ``None``.
    """
    func_line: int = node.lineno
    open_paren_idx: int | None = _find_def_open_paren(
        tokens, func_line=func_line, name=node.name,
    )
    if open_paren_idx is None:
        return None

    has_self_cls: bool = bool(
        node.args.args and node.args.args[0].arg in ("self", "cls")
    )

    if has_self_cls:
        return _insert_after_first_param(tokens, paren_idx=open_paren_idx)
    return _insert_after_open_paren(tokens, paren_idx=open_paren_idx)


def _find_def_open_paren(
    tokens: list[TokenInfo],
    *,
    func_line: int,
    name: str,
) -> int | None:
    """Find the index of the ``(`` token for a function definition."""
    for token_idx, token in enumerate(tokens):
        if (
            token.type == tokenize.NAME
            and token.string == "def"
            and token.start[0] == func_line
            and token_idx + 1 < len(tokens)
            and tokens[token_idx + 1].string == name
        ):
            for search_idx in range(token_idx + 2, len(tokens)):
                if tokens[search_idx].type == tokenize.OP and tokens[search_idx].string == "(":
                    return search_idx
            break
    return None


def _insert_after_open_paren(
    tokens: list[TokenInfo],
    *,
    paren_idx: int,
) -> tuple[int, int, str] | None:
    """Insert ``*, `` right after the opening ``(``."""
    paren_token: TokenInfo = tokens[paren_idx]
    line_0indexed: int = paren_token.end[0] - 1
    col: int = paren_token.end[1]
    return (line_0indexed, col, "*, ")


def _insert_after_first_param(
    tokens: list[TokenInfo],
    *,
    paren_idx: int,
) -> tuple[int, int, str] | None:
    """Insert ``*, `` after the comma following the first parameter (self/cls)."""
    depth: int = 0
    for token_idx in range(paren_idx, len(tokens)):
        token: TokenInfo = tokens[token_idx]
        if token.type == tokenize.OP and token.string == "(":
            depth += 1
        elif token.type == tokenize.OP and token.string == ")":
            depth -= 1
            if depth == 0:
                break
        elif token.type == tokenize.OP and token.string == "," and depth == 1:
            # Found the comma after self/cls — insert after it
            line_0indexed: int = token.end[0] - 1
            col: int = token.end[1]
            next_idx: int = token_idx + 1
            if next_idx < len(tokens) and tokens[next_idx].type == tokenize.NL:
                next_idx += 1
            if next_idx < len(tokens):
                next_token: TokenInfo = tokens[next_idx]
                if next_token.start[0] == token.end[0] and next_token.start[1] > token.end[1]:
                    return (line_0indexed, col + 1, "*, ")
            return (line_0indexed, col, " *, ")
    return None


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
