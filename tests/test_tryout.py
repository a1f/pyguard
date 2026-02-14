"""Tests for pyguard fix --tryout interactive mode."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pyguard.cli import cli


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


class TestTryoutYes:
    """Test 'y' (yes) response applies the fix."""

    def test_y_applies_fix(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="y\n",
        )

        assert result.exit_code == 0
        assert target.read_text() == _FIXED_SOURCE
        assert "Applied 1 of 1 file." in result.output


class TestTryoutNo:
    """Test 'n' (no) response skips the fix."""

    def test_n_skips_fix(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="n\n",
        )

        assert result.exit_code == 0
        assert target.read_text() == _FIXABLE_SOURCE
        assert "Applied 0 of 1 files." in result.output


class TestTryoutAll:
    """Test 'a' (all) response applies all remaining."""

    def test_a_applies_all_remaining(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "b.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "c.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        # First file: 'a' (apply all remaining)
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="a\n",
        )

        assert result.exit_code == 0
        assert (tmp_path / "a.py").read_text() == _FIXED_SOURCE
        assert (tmp_path / "b.py").read_text() == _FIXED_SOURCE
        assert (tmp_path / "c.py").read_text() == _FIXED_SOURCE
        assert "Applied 3 of 3 files." in result.output


class TestTryoutQuit:
    """Test 'q' (quit) response stops immediately."""

    def test_q_stops_early(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "b.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="q\n",
        )

        assert result.exit_code == 0
        # First file not applied, second never reached
        assert (tmp_path / "a.py").read_text() == _FIXABLE_SOURCE
        assert (tmp_path / "b.py").read_text() == _FIXABLE_SOURCE
        assert "Applied 0 of 2 files." in result.output


class TestTryoutMixed:
    """Test mixed responses."""

    def test_y_then_n(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)
        (tmp_path / "b.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="y\nn\n",
        )

        assert result.exit_code == 0
        assert (tmp_path / "a.py").read_text() == _FIXED_SOURCE
        assert (tmp_path / "b.py").read_text() == _FIXABLE_SOURCE
        assert "Applied 1 of 2 file." in result.output


class TestTryoutNoChanges:
    """Test tryout with no changes needed."""

    def test_no_changes_shows_summary(self, tmp_path: Path) -> None:
        (tmp_path / "clean.py").write_text(_CLEAN_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["fix", "--tryout", str(tmp_path)])

        assert result.exit_code == 0
        assert "Applied 0 of 0 files." in result.output


class TestTryoutMutualExclusion:
    """Test that --tryout is mutually exclusive with --diff and --check."""

    def test_tryout_with_diff_errors(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", "--diff", str(tmp_path)],
        )

        assert result.exit_code == 2
        assert "mutually exclusive" in result.output

    def test_tryout_with_check_errors(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", "--check", str(tmp_path)],
        )

        assert result.exit_code == 2
        assert "mutually exclusive" in result.output


class TestTryoutShowsDiff:
    """Test that tryout shows diff for each file."""

    def test_tryout_shows_diff(self, tmp_path: Path) -> None:
        target: Path = tmp_path / "fixable.py"
        target.write_text(_FIXABLE_SOURCE)

        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["fix", "--tryout", str(tmp_path)], input="y\n",
        )

        assert "---" in result.output
        assert "+++" in result.output
        assert "-def greet(name: str):" in result.output
        assert "+def greet(name: str) -> None:" in result.output
