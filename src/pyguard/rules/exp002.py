"""EXP002: Enforce __all__ or explicit re-export policy."""
from __future__ import annotations

import ast

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


class EXP002Rule:
    """Detect modules with public symbols but no __all__ definition."""

    @property
    def code(self) -> str:
        return "EXP002"

    def check(
        self,
        *,
        parse_result: ParseResult,
        config: PyGuardConfig,
    ) -> list[Diagnostic]:
        if parse_result.tree is None:
            return []

        severity: Severity = config.get_severity("EXP002")

        if _has_all_definition(parse_result.tree):
            return []

        if not _has_public_symbols(parse_result.tree):
            return []

        source_line: str | None = None
        if parse_result.source_lines:
            source_line = parse_result.source_lines[0]

        return [
            Diagnostic(
                file=parse_result.file,
                location=SourceLocation(line=1, column=1),
                code="EXP002",
                message="Module should define '__all__' to explicitly "
                "declare public API",
                severity=severity,
                source_line=source_line,
            ),
        ]


def _has_all_definition(tree: ast.Module) -> bool:
    """Check if __all__ is assigned at module level."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return True
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
        ):
            return True
        if (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "__all__"
        ):
            return True
    return False


def _has_public_symbols(tree: ast.Module) -> bool:
    """Check if the module has any public (non-underscore) symbols."""
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ) and not node.name.startswith("_"):
            return True
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and not target.id.startswith("_")
                ):
                    return True
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and not node.target.id.startswith("_")
        ):
            return True
    return False
