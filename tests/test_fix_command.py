"""Tests for the pyguard fix CLI command."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pyguard.cli import cli


# Source that triggers TYP002 (missing -> None) fixer
_FIXABLE_SOURCE: str = """\
def greet(name: str):
    print(name)
"""

_FIXED_SOURCE: str = """\
def greet(name: str) -> None:
    print(name)
"""

_CLEAN_SOURCE: str = """\
def greet(name: str) -> None:
    print(name)
"""

_SYNTAX_ERROR_SOURCE: str = """\
def broken(
"""


class TestFixInPlace:
    """Test default fix mode (write files in-place)."""

    def test_fix_writes_changed_file(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", str(tmp_path)])

        assert result.exit_code == 0
        assert "Fixed 1 file." in result.output
        assert target.read_text() == _FIXED_SOURCE

    def test_fix_clean_file_no_changes(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "clean.py"
        target.write_text(_CLEAN_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", str(tmp_path)])

        assert result.exit_code == 0
        assert "Fixed 0 files." in result.output
        assert target.read_text() == _CLEAN_SOURCE

    def test_fix_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "b.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "c.py").write_text(_CLEAN_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", str(tmp_path)])

        assert result.exit_code == 0
        assert "Fixed 2 files." in result.output

    def test_fix_skips_syntax_errors(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text(_SYNTAX_ERROR_SOURCE)
        (tmp_path / "good.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", str(tmp_path)])

        assert result.exit_code == 0
        assert "Fixed 1 file." in result.output
        # Syntax error file left unchanged
        assert (tmp_path / "bad.py").read_text() == _SYNTAX_ERROR_SOURCE


class TestFixDiff:
    """Test --diff mode."""

    def test_diff_shows_unified_diff(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", "--diff", str(tmp_path)])

        assert result.exit_code == 0
        assert "---" in result.output
        assert "+++" in result.output
        assert "-def greet(name: str):" in result.output
        assert "+def greet(name: str) -> None:" in result.output

    def test_diff_does_not_write(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        runner.invoke(cli, ["fix", "--diff", str(tmp_path)])

        # File should be unchanged
        assert target.read_text() == _FIXABLE_SOURCE

    def test_diff_clean_file_no_output(self, tmp_path: Path) -> None:
        (tmp_path / "clean.py").write_text(_CLEAN_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", "--diff", str(tmp_path)])

        assert result.exit_code == 0
        assert "---" not in result.output
        assert "0 files would be changed." in result.output


class TestFixCheck:
    """Test --check mode (CI)."""

    def test_check_exits_1_when_changes_needed(self, tmp_path: Path) -> None:
        (tmp_path / "fixable.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", "--check", str(tmp_path)])

        assert result.exit_code == 1
        assert "1 file would be changed." in result.output

    def test_check_exits_0_when_clean(self, tmp_path: Path) -> None:
        (tmp_path / "clean.py").write_text(_CLEAN_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", "--check", str(tmp_path)])

        assert result.exit_code == 0
        assert "No changes needed." in result.output

    def test_check_does_not_write(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        runner.invoke(cli, ["fix", "--check", str(tmp_path)])

        assert target.read_text() == _FIXABLE_SOURCE


class TestFixExcludePatterns:
    """Test that fix respects exclude patterns."""

    def test_fix_respects_exclude_config(self, tmp_path: Path) -> None:
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard]
include = ["**/*.py"]
exclude = ["**/excluded/**"]
"""
        )
        excluded_dir: Path = tmp_path / "excluded"
        excluded_dir.mkdir()
        (excluded_dir / "skip.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "include.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "fix", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert "Fixed 1 file." in result.output
        # Excluded file untouched
        assert (excluded_dir / "skip.py").read_text() == _FIXABLE_SOURCE


class TestFixEmptyDirectory:
    """Test fix on empty directories."""

    def test_fix_empty_directory(self, tmp_path: Path) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", str(tmp_path)])

        assert result.exit_code == 0
        assert "Fixed 0 files." in result.output
