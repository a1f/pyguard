"""AST parsing with syntax error detection for PyGuard."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SyntaxErrorInfo:
    """Syntax error details. Line/column are 1-based."""

    line: int
    column: int
    message: str
    source_line: str | None


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Result of parsing a Python file."""

    file: Path
    tree: ast.Module | None
    source: str
    source_lines: tuple[str, ...]
    syntax_error: SyntaxErrorInfo | None


def parse_file(*, file: Path) -> ParseResult:
    """Parse a Python file, returning AST or syntax error."""
    try:
        source: str = file.read_text(encoding="utf-8")
    except OSError as e:
        return ParseResult(
            file=file,
            tree=None,
            source="",
            source_lines=(),
            syntax_error=SyntaxErrorInfo(
                line=1,
                column=1,
                message=f"Cannot read file: {e}",
                source_line=None,
            ),
        )
    except UnicodeDecodeError as e:
        return ParseResult(
            file=file,
            tree=None,
            source="",
            source_lines=(),
            syntax_error=SyntaxErrorInfo(
                line=1,
                column=1,
                message=f"Encoding error: {e}",
                source_line=None,
            ),
        )

    source_lines: tuple[str, ...] = tuple(source.splitlines())

    try:
        tree: ast.Module = ast.parse(source, filename=str(file))
    except SyntaxError as e:
        line: int = e.lineno if e.lineno is not None else 1
        column: int = max(1, e.offset if e.offset is not None else 1)

        source_line: str | None = None
        if 1 <= line <= len(source_lines):
            source_line = source_lines[line - 1]

        return ParseResult(
            file=file,
            tree=None,
            source=source,
            source_lines=source_lines,
            syntax_error=SyntaxErrorInfo(
                line=line,
                column=column,
                message=e.msg or "Syntax error",
                source_line=source_line,
            ),
        )

    return ParseResult(
        file=file,
        tree=tree,
        source=source,
        source_lines=source_lines,
        syntax_error=None,
    )
