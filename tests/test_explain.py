"""Tests for the pyguard explain command."""
from __future__ import annotations

from click.testing import CliRunner

from pyguard.cli import cli
from pyguard.constants import RULE_CODES
from pyguard.explain import RULE_CATALOG


class TestExplainSingleRule:
    """Test explain for a single rule."""

    def test_explain_typ001(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "TYP001"])

        assert result.exit_code == 0
        assert "TYP001: Missing Parameter Annotations" in result.output
        assert "Category: typing" in result.output
        assert "Autofix: No" in result.output
        assert "Bad:" in result.output
        assert "Good:" in result.output
        assert "Suppress:" in result.output

    def test_explain_typ002_shows_fix(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "TYP002"])

        assert result.exit_code == 0
        assert "Autofix: Yes" in result.output
        assert "Fix:" in result.output

    def test_explain_kw001_shows_config(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "KW001"])

        assert result.exit_code == 0
        assert "Config:" in result.output
        assert "min_params" in result.output

    def test_explain_lowercase_code(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "typ001"])

        assert result.exit_code == 0
        assert "TYP001" in result.output

    def test_explain_unknown_code_exits_1(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "FAKE999"])

        assert result.exit_code == 1
        assert "Unknown rule code" in result.output


class TestExplainAll:
    """Test explain --all listing."""

    def test_all_lists_all_rules(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "--all"])

        assert result.exit_code == 0
        for code in RULE_CODES:
            assert code in result.output

    def test_all_shows_table_header(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "--all"])

        assert result.exit_code == 0
        assert "CODE" in result.output
        assert "SEVERITY" in result.output
        assert "NAME" in result.output
        assert "FIX" in result.output

    def test_all_shows_autofix_markers(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain", "--all"])

        assert result.exit_code == 0
        assert "Yes" in result.output  # Some rules have autofix


class TestExplainNoArgs:
    """Test explain with no arguments."""

    def test_no_args_shows_usage(self) -> None:
        runner: CliRunner = CliRunner()
        result = runner.invoke(cli, ["explain"])

        assert result.exit_code == 1
        assert "Usage:" in result.output


class TestRuleCatalogCoverage:
    """Test that the catalog covers all defined rule codes."""

    def test_catalog_covers_all_rule_codes(self) -> None:
        assert set(RULE_CATALOG.keys()) == RULE_CODES

    def test_all_catalog_entries_have_examples(self) -> None:
        for code, info in RULE_CATALOG.items():
            assert info.bad_example, f"{code} missing bad_example"
            assert info.good_example, f"{code} missing good_example"

    def test_all_catalog_entries_have_descriptions(self) -> None:
        for code, info in RULE_CATALOG.items():
            assert info.description, f"{code} missing description"
            assert info.name, f"{code} missing name"
