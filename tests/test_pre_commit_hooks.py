"""Tests for pre-commit hooks configuration."""
from __future__ import annotations

from pathlib import Path

_HOOKS_FILE: Path = Path(__file__).parent.parent / ".pre-commit-hooks.yaml"


class TestPreCommitHooksFile:
    """Test .pre-commit-hooks.yaml structure and content."""

    def test_hooks_file_exists(self) -> None:
        assert _HOOKS_FILE.exists()

    def test_hooks_file_is_valid_yaml(self) -> None:
        content: str = _HOOKS_FILE.read_text()
        # Basic structure check: should have id, name, language, entry, types
        assert "- id:" in content

    def test_lint_hook_defined(self) -> None:
        content: str = _HOOKS_FILE.read_text()
        assert "id: pyguard-lint" in content
        assert "entry: pyguard lint" in content
        assert "language: python" in content
        assert "types: [python]" in content

    def test_fix_hook_defined(self) -> None:
        content: str = _HOOKS_FILE.read_text()
        assert "id: pyguard-fix" in content
        assert "entry: pyguard fix --check" in content
        assert "language: python" in content

    def test_hook_ids_are_unique(self) -> None:
        content: str = _HOOKS_FILE.read_text()
        ids: list[str] = [
            line.split("id:")[1].strip()
            for line in content.splitlines()
            if line.strip().startswith("- id:")
        ]
        assert len(ids) == len(set(ids))
        assert len(ids) == 2

    def test_all_hooks_have_required_fields(self) -> None:
        content: str = _HOOKS_FILE.read_text()
        # Split into hook blocks
        blocks: list[str] = content.split("- id:")[1:]
        for block in blocks:
            assert "name:" in block
            assert "language:" in block
            assert "entry:" in block
            assert "types:" in block
