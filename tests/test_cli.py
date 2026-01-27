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

    def test_lint_shows_config_loaded(self, tmp_path: Path) -> None:
        """lint command should show it loaded config."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", str(tmp_path)])

        assert result.exit_code == 0
        assert "Would lint paths:" in result.output
        assert "Using config from:" in result.output

    def test_lint_with_format_override(self, tmp_path: Path) -> None:
        """lint --format should override config."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", "--format", "json", str(tmp_path)])

        assert result.exit_code == 0
        assert "Format: json" in result.output

    def test_lint_with_color_override(self, tmp_path: Path) -> None:
        """lint --color should override config."""
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["lint", "--color", "never", str(tmp_path)])

        assert result.exit_code == 0
        assert "Color: never" in result.output


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
