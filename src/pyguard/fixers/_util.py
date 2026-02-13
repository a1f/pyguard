"""Shared utilities for fixer modules."""
from __future__ import annotations

import ast
import io
import tokenize
from tokenize import TokenInfo


def tokenize_source(source: str) -> list[TokenInfo]:
    """Tokenize source code, returning empty list on error."""
    try:
        return list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return []


def parse_source(source: str) -> ast.Module | None:
    """Parse source code, returning ``None`` on error."""
    try:
        return ast.parse(source)
    except (SyntaxError, RecursionError, ValueError):
        return None


def apply_insertions(source: str, lines: list[str]) -> str:
    """Join modified lines and validate the result is still valid Python.

    Returns the original *source* unchanged if the modified output
    fails to parse — a defence-in-depth guard against malformed edits.
    """
    result: str = "".join(lines)
    if parse_source(result) is None:
        return source
    return result
