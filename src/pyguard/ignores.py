"""Ignore pragma parsing and diagnostic filtering for PyGuard."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pyguard.constants import IGN001_CODE, IGN002_CODE, IGN003_CODE, Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import IgnoreGovernance

_IGNORE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"#\s*pyguard:\s*ignore\[([^\]]+)\](?:\s+because:\s*(.+))?$"
)
_IGNORE_FILE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"#\s*pyguard:\s*ignore-file\[([^\]]+)\](?:\s+because:\s*(.+))?$"
)


@dataclass(frozen=True, slots=True)
class IgnoreDirective:
    line: int
    codes: frozenset[str]
    reason: str | None
    is_file_level: bool
    is_inline: bool


def parse_ignore_directives(
    *,
    source_lines: tuple[str, ...],
) -> list[IgnoreDirective]:
    directives: list[IgnoreDirective] = []

    for idx, line_text in enumerate(source_lines):
        line_num: int = idx + 1

        file_match: re.Match[str] | None = _IGNORE_FILE_PATTERN.search(line_text)
        if file_match is not None:
            codes: frozenset[str] = _parse_codes(file_match.group(1))
            reason: str | None = _clean_reason(file_match.group(2))
            directives.append(IgnoreDirective(
                line=line_num,
                codes=codes,
                reason=reason,
                is_file_level=True,
                is_inline=False,
            ))
            continue

        match: re.Match[str] | None = _IGNORE_PATTERN.search(line_text)
        if match is not None:
            codes = _parse_codes(match.group(1))
            reason = _clean_reason(match.group(2))
            before_comment: str = line_text[:match.start()].strip()
            is_inline: bool = len(before_comment) > 0
            directives.append(IgnoreDirective(
                line=line_num,
                codes=codes,
                reason=reason,
                is_file_level=False,
                is_inline=is_inline,
            ))

    return directives


def apply_ignores(
    *,
    diagnostics: list[Diagnostic],
    parse_result: ParseResult,
    governance: IgnoreGovernance,
) -> list[Diagnostic]:
    """Also enforces governance rules — returned list may include IGN0xx violations."""
    directives: list[IgnoreDirective] = parse_ignore_directives(
        source_lines=parse_result.source_lines,
    )

    if not directives:
        return diagnostics

    governance_violations: list[Diagnostic] = _check_governance(
        directives=directives,
        governance=governance,
        file=parse_result.file,
        source_lines=parse_result.source_lines,
    )

    file_codes: frozenset[str] = frozenset()
    for d in directives:
        if d.is_file_level:
            file_codes = file_codes | d.codes

    line_ignores: dict[int, frozenset[str]] = {}
    for d in directives:
        if not d.is_file_level and d.is_inline:
            existing: frozenset[str] = line_ignores.get(d.line, frozenset())
            line_ignores[d.line] = existing | d.codes

    block_ranges: list[tuple[int, int, frozenset[str]]] = _resolve_block_ranges(
        directives=directives,
        tree=parse_result.tree,
    )

    disallowed: frozenset[str] = governance.disallow
    kept: list[Diagnostic] = []
    for diag in diagnostics:
        if diag.code in disallowed:
            kept.append(diag)
            continue

        if diag.code in file_codes:
            continue

        line_codes: frozenset[str] | None = line_ignores.get(diag.location.line)
        if line_codes is not None and diag.code in line_codes:
            continue

        if any(
            start <= diag.location.line <= end and diag.code in codes
            for start, end, codes in block_ranges
        ):
            continue

        kept.append(diag)

    return governance_violations + kept


def _parse_codes(raw: str) -> frozenset[str]:
    return frozenset(c.strip().upper() for c in raw.split(",") if c.strip())


def _clean_reason(raw: str | None) -> str | None:
    if raw is None:
        return None
    stripped: str = raw.strip()
    return stripped if stripped else None


def _collect_statement_ranges(*, tree: ast.Module) -> dict[int, int]:
    """Map effective_start_line -> end_line for all statements in the AST."""
    ranges: dict[int, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        start: int = node.lineno
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.decorator_list
        ):
            start = min(d.lineno for d in node.decorator_list)
        end: int = node.end_lineno or node.lineno
        ranges[start] = end
    return ranges


def _resolve_block_ranges(
    *,
    directives: list[IgnoreDirective],
    tree: ast.Module | None,
) -> list[tuple[int, int, frozenset[str]]]:
    block_directives: list[IgnoreDirective] = [
        d for d in directives if not d.is_file_level and not d.is_inline
    ]
    if not block_directives or tree is None:
        return []

    stmt_ranges: dict[int, int] = _collect_statement_ranges(tree=tree)
    result: list[tuple[int, int, frozenset[str]]] = []
    for directive in block_directives:
        next_line: int = directive.line + 1
        end_line: int | None = stmt_ranges.get(next_line)
        if end_line is not None:
            result.append((next_line, end_line, directive.codes))

    return result


def _check_governance(
    *,
    directives: list[IgnoreDirective],
    governance: IgnoreGovernance,
    file: Path,
    source_lines: tuple[str, ...],
) -> list[Diagnostic]:
    violations: list[Diagnostic] = []

    if governance.require_reason:
        for d in directives:
            if d.reason is None:
                violations.append(Diagnostic(
                    file=file,
                    location=SourceLocation(line=d.line, column=1),
                    code=IGN001_CODE,
                    message="Ignore pragma requires a reason (use 'because: ...')",
                    severity=Severity.ERROR,
                    source_line=_get_source_line(d.line, source_lines),
                ))

    for d in directives:
        for code in sorted(d.codes):
            if code in governance.disallow:
                violations.append(Diagnostic(
                    file=file,
                    location=SourceLocation(line=d.line, column=1),
                    code=IGN002_CODE,
                    message=f"Rule '{code}' cannot be ignored "
                    f"(disallowed by configuration)",
                    severity=Severity.ERROR,
                    source_line=_get_source_line(d.line, source_lines),
                ))

    if (
        governance.max_per_file is not None
        and len(directives) > governance.max_per_file
    ):
        violations.append(Diagnostic(
            file=file,
            location=SourceLocation(line=1, column=1),
            code=IGN003_CODE,
            message=f"File has {len(directives)} ignore directives, "
            f"maximum allowed is {governance.max_per_file}",
            severity=Severity.ERROR,
            source_line=_get_source_line(1, source_lines),
        ))

    return violations


def _get_source_line(line: int, source_lines: tuple[str, ...]) -> str | None:
    if 1 <= line <= len(source_lines):
        return source_lines[line - 1]
    return None
