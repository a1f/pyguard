"""IMP001 fixer: Move local imports to module level."""
from __future__ import annotations

import ast
import sys

from pyguard.fixers._util import parse_source

_STDLIB_MODULES: frozenset[str] = (
    frozenset(sys.stdlib_module_names)
    if hasattr(sys, "stdlib_module_names")
    else frozenset()
)


def fix_local_imports(source: str) -> str:
    """
    Fix IMP001: move function-level imports to module level.

    Only handles simple, single-line imports.  Skips conditional
    imports (try/except ImportError) and multi-line imports.
    """
    tree: ast.Module | None = parse_source(source)
    if tree is None:
        return source

    lines: list[str] = source.splitlines(keepends=True)
    if not lines:
        return source

    collector: _ImportCollector = _ImportCollector()
    collector.visit(tree)

    if not collector.local_imports:
        return source

    # Existing module-level import texts (stripped)
    existing_texts: set[str] = set()
    for node in collector.module_imports:
        line_idx: int = node.lineno - 1
        if 0 <= line_idx < len(lines):
            existing_texts.add(lines[line_idx].strip())

    # Determine lines to remove and new imports to add
    lines_to_remove: set[int] = set()
    new_import_texts: list[str] = []

    for node in collector.local_imports:
        # Skip multi-line imports for safety
        if node.end_lineno is not None and node.end_lineno > node.lineno:
            continue
        line_idx = node.lineno - 1
        if 0 <= line_idx < len(lines):
            lines_to_remove.add(line_idx)
            text: str = lines[line_idx].strip()
            if text not in existing_texts and text not in new_import_texts:
                new_import_texts.append(text)

    if not lines_to_remove:
        return source

    # Remove local import lines
    kept_lines: list[str] = [
        line for idx, line in enumerate(lines) if idx not in lines_to_remove
    ]

    if not new_import_texts:
        # All were duplicates — just return with removals
        result: str = "".join(kept_lines)
        if parse_source(result) is None:
            return source
        return result

    # Separate stdlib from non-stdlib
    stdlib_texts: list[str] = [
        t for t in new_import_texts if _is_stdlib_import(t)
    ]
    other_texts: list[str] = [
        t for t in new_import_texts if not _is_stdlib_import(t)
    ]

    # Build import block
    import_block: list[str] = []
    for imp in stdlib_texts:
        import_block.append(imp + "\n")
    if stdlib_texts and other_texts:
        import_block.append("\n")
    for imp in other_texts:
        import_block.append(imp + "\n")

    # Find insertion position
    insert_pos: int = 0
    if not stdlib_texts:
        insert_pos = _after_last_import(kept_lines)

    # Add blank line separator if next line is non-blank
    if insert_pos < len(kept_lines) and kept_lines[insert_pos].strip():
        import_block.append("\n")

    # Insert the block
    for i, imp_line in enumerate(import_block):
        kept_lines.insert(insert_pos + i, imp_line)

    result = "".join(kept_lines)
    if parse_source(result) is None:
        return source
    return result


def _after_last_import(lines: list[str]) -> int:
    """Return the line index after the last top-level import."""
    last_import: int = -1
    for idx, line in enumerate(lines):
        stripped: str = line.strip()
        if stripped.startswith(("import ", "from ")):
            last_import = idx
    return last_import + 1 if last_import >= 0 else 0


def _is_stdlib_import(import_text: str) -> bool:
    """Check whether an import statement refers to a stdlib module."""
    text: str = import_text.strip()
    if text.startswith("from "):
        parts: list[str] = text.split()
        module: str = parts[1] if len(parts) > 1 else ""
    elif text.startswith("import "):
        parts = text.split()
        module = parts[1].rstrip(",") if len(parts) > 1 else ""
    else:
        return False
    top_level: str = module.split(".")[0]
    return top_level in _STDLIB_MODULES


def _is_type_checking_guard(test: ast.expr) -> bool:
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return (
        isinstance(test, ast.Attribute)
        and isinstance(test.value, ast.Name)
        and test.attr == "TYPE_CHECKING"
    )


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in (
        "ImportError",
        "ModuleNotFoundError",
    ):
        return True
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(elt, ast.Name)
            and elt.id in ("ImportError", "ModuleNotFoundError")
            for elt in handler.type.elts
        )
    return False


class _ImportCollector(ast.NodeVisitor):
    """Collect module-level and function-level import nodes."""

    def __init__(self) -> None:
        self._function_depth: int = 0
        self._in_type_checking: bool = False
        self._in_try_except_import: bool = False
        self.module_imports: list[ast.Import | ast.ImportFrom] = []
        self.local_imports: list[ast.Import | ast.ImportFrom] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_depth += 1
        self.generic_visit(node)
        self._function_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            prev: bool = self._in_type_checking
            self._in_type_checking = True
            for child in node.body:
                self.visit(child)
            self._in_type_checking = prev
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        if any(_catches_import_error(h) for h in node.handlers):
            prev: bool = self._in_try_except_import
            self._in_try_except_import = True
            self.generic_visit(node)
            self._in_try_except_import = prev
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self._collect(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._collect(node)

    def _collect(self, node: ast.Import | ast.ImportFrom) -> None:
        if self._in_type_checking or self._in_try_except_import:
            return
        if self._function_depth > 0:
            self.local_imports.append(node)
        else:
            self.module_imports.append(node)
