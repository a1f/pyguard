"""Tests for PyGuard CLI."""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pyguard.cli import cli
from pyguard.constants import __version__


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_help_shows_usage(self) -> None:
        """--help should show usage information."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "PyGuard" in result.output
        assert "config" in result.output
        assert "lint" in result.output

    def test_version_shows_version(self) -> None:
        """--version should show version number."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output


class TestConfigCommand:
    """Test the config command."""

    def test_config_shows_resolved_config(self) -> None:
        """config command should show resolved configuration."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["config"])

        assert result.exit_code == 0
        assert "PyGuard Configuration" in result.output
        assert "Python version:" in result.output
        assert "Rule Severities:" in result.output

    def test_config_json_outputs_valid_json(self) -> None:
        """config --json should output valid JSON."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["config", "--json"])

        assert result.exit_code == 0

        data: dict[str, object] = json.loads(result.output)
        assert "python_version" in data
        assert "rules" in data
        assert "ignores" in data

    def test_config_validate_succeeds(self) -> None:
        """config --validate should succeed with valid config."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["config", "--validate"])

        assert result.exit_code == 0
        assert "Configuration valid" in result.output


class TestLintCommand:
    """Test the lint command."""

    def test_lint_clean_directory(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text("x: int = 1\n")
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", str(tmp_path)])

        assert result.exit_code == 0
        assert "No issues found." in result.output
        assert "Checked 1 file." in result.output

    def test_lint_syntax_error(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text("def broken(\n")
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", str(tmp_path)])

        assert result.exit_code == 1
        assert "SYN001" in result.output
        assert "1 error" in result.output

    def test_lint_empty_directory(self, tmp_path: Path) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", str(tmp_path)])

        assert result.exit_code == 0
        assert "No issues found." in result.output
        assert "Checked 0 files." in result.output

    def test_lint_json_format(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text("def broken(\n")
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", "--format", "json", str(tmp_path)])

        assert result.exit_code == 1
        assert '"code": "SYN001"' in result.output

    def test_lint_no_show_source(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text("def broken(\n")
        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["lint", "--no-show-source", str(tmp_path)],
        )

        assert result.exit_code == 1
        assert "SYN001" in result.output
        # Source line should not appear with caret
        assert "    ^" not in result.output


class TestConfigDisplay:
    """Test config display edge cases."""

    def test_max_per_file_zero_displays_zero(self, tmp_path: Path) -> None:
        """max_per_file=0 should display as 0, not 'unlimited'."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard.ignores]
max_per_file = 0
"""
        )
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "config"])

        assert result.exit_code == 0
        assert "Max per file: 0" in result.output
        assert "unlimited" not in result.output


class TestErrorHandling:
    """Test CLI error handling."""

    def test_invalid_config_exits_with_error(self, tmp_path: Path) -> None:
        """Invalid config should exit with error code 1."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard]
output_format = "invalid"
"""
        )

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "config"])

        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_explicit_config_path(self, tmp_path: Path) -> None:
        """--config should use explicit config path."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard]
python_version = "3.12"
"""
        )

        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "config"])

        assert result.exit_code == 0
        assert "Python version: 3.12" in result.output
