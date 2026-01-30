"""File discovery for PyGuard using glob patterns."""
from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from pyguard.types import PyGuardConfig


def _matches_pattern(*, path: Path, patterns: tuple[str, ...], base: Path) -> bool:
    """Check if path matches any of the glob patterns."""
    try:
        rel_path: Path = path.relative_to(base)
    except ValueError:
        rel_path = path

    rel_str: str = str(rel_path).replace("\\", "/")

    return any(_glob_match(path=rel_str, pattern=pattern) for pattern in patterns)


def _glob_match(*, path: str, pattern: str) -> bool:
    """Match a path against a glob pattern with ** support."""
    if "**" in pattern:
        return _match_doublestar(path=path, pattern=pattern)
    return fnmatch(path, pattern)


def _match_doublestar(*, path: str, pattern: str) -> bool:
    """Match path against pattern containing **."""
    parts: list[str] = path.split("/")

    # Pattern like "**/*.py" - match any .py file at any depth
    if pattern == "**/*.py":
        return path.endswith(".py")

    # Pattern like "**/name/**" - check if name is in path components
    if pattern.startswith("**/") and pattern.endswith("/**"):
        middle: str = pattern[3:-3]  # Strip **/ and /**
        # Handle wildcards in middle (e.g., ".*" for dotfiles)
        return any(fnmatch(part, middle) for part in parts[:-1])

    # Pattern like "**/name" - check if any suffix matches
    if pattern.startswith("**/"):
        suffix: str = pattern[3:]  # Strip **/
        for i in range(len(parts)):
            candidate: str = "/".join(parts[i:])
            if fnmatch(candidate, suffix):
                return True
        return False

    # Pattern like "prefix/**/*.py" - prefix must match, then any .py
    if "/**/" in pattern:
        prefix: str
        tail: str
        prefix, tail = pattern.split("/**/", 1)
        if not path.startswith(prefix + "/"):
            return False
        remainder: str = path[len(prefix) + 1:]
        # Tail could be "*.py" - match against any part of remainder
        remainder_parts: list[str] = remainder.split("/")
        return any(
            fnmatch("/".join(remainder_parts[i:]), tail)
            for i in range(len(remainder_parts))
        )

    # Pattern like "prefix/**" - anything under prefix
    if pattern.endswith("/**"):
        prefix = pattern[:-3]  # Strip /**
        return path.startswith(prefix + "/") or path == prefix

    # Fallback to fnmatch
    return fnmatch(path, pattern)


def _collect_python_files(*, path: Path) -> list[Path]:
    """Recursively collect all .py files under a path."""
    files: list[Path] = []
    if path.is_file():
        if path.suffix == ".py":
            files.append(path)
    elif path.is_dir():
        for child in path.iterdir():
            files.extend(_collect_python_files(path=child))
    return files


def scan_files(*, paths: tuple[Path, ...], config: PyGuardConfig) -> list[Path]:
    """
    Find Python files matching include/exclude patterns.

    Args:
        paths: Root paths to scan (files or directories).
        config: PyGuard configuration with include/exclude patterns.

    Returns:
        Sorted list of Python files to lint.
    """
    all_files: list[Path] = []

    for path in paths:
        resolved: Path = path.resolve()
        all_files.extend(_collect_python_files(path=resolved))

    filtered: set[Path] = set()
    for file_path in all_files:
        base: Path = file_path.parent
        for input_path in paths:
            resolved_input: Path = input_path.resolve()
            # If input was a file (not directory), use its parent as base
            if resolved_input.is_file():
                if file_path == resolved_input:
                    base = resolved_input.parent
                    break
            else:
                try:
                    file_path.relative_to(resolved_input)
                    base = resolved_input
                    break
                except ValueError:
                    continue

        # Exclusions take priority
        if _matches_pattern(path=file_path, patterns=config.exclude, base=base):
            continue

        if _matches_pattern(path=file_path, patterns=config.include, base=base):
            filtered.add(file_path)

    # Return sorted for deterministic output
    return sorted(filtered)
