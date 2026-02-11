"""Tests for the PyGuard rule framework (protocol, registry, runner integration)."""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.parser import ParseResult
from pyguard.rules.base import Rule
import pyguard.rules.registry as registry_mod
from pyguard.rules.registry import get_enabled_rules
from pyguard.runner import LintResult, lint_paths
from pyguard.types import PyGuardConfig, RuleConfig


def _write_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class FakeRule:
    """A fake rule for testing the framework."""

    @property
    def code(self) -> str:
        return "FAKE01"

    def check(
        self,
        *,
        parse_result: ParseResult,
        config: PyGuardConfig,
    ) -> list[Diagnostic]:
        return [
            Diagnostic(
                file=parse_result.file,
                location=SourceLocation(line=1, column=1),
                code=self.code,
                message="Fake diagnostic",
                severity=config.get_severity(self.code),
            ),
        ]


class TestRuleProtocol:
    def test_fake_rule_satisfies_protocol(self) -> None:
        rule: FakeRule = FakeRule()
        assert isinstance(rule, Rule)

    def test_fake_rule_has_code(self) -> None:
        rule: FakeRule = FakeRule()
        assert rule.code == "FAKE01"


class TestRegistry:
    def test_get_enabled_rules_returns_registered_rules(self) -> None:
        rules: list[Rule] = get_enabled_rules(config=PyGuardConfig())
        assert isinstance(rules, list)
        assert len(rules) >= 1
        codes: list[str] = [r.code for r in rules]
        assert "TYP001" in codes

    def test_get_enabled_rules_excludes_off_rules(self) -> None:
        severities: dict[str, Severity] = {"TYP001": Severity.OFF}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        rules: list[Rule] = get_enabled_rules(config=config)
        codes: list[str] = [r.code for r in rules]
        assert "TYP001" not in codes


class TestRunnerRuleIntegration:
    def test_rules_run_on_valid_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rules should produce diagnostics for valid (parseable) files."""
        _write_file(tmp_path / "good.py", "x: int = 1\n")

        fake_rule: FakeRule = FakeRule()

        monkeypatch.setattr(registry_mod, "_all_rules", lambda: [fake_rule])

        severities: dict[str, Severity] = {"FAKE01": Severity.WARN}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)

        assert result.files_checked == 1
        assert len(result.diagnostics) == 1
        diag: Diagnostic = result.diagnostics.sorted[0]
        assert diag.code == "FAKE01"
        assert diag.severity == Severity.WARN

    def test_rules_skipped_on_syntax_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rules should NOT run on files with syntax errors."""
        _write_file(tmp_path / "bad.py", "def broken(\n")

        call_count: list[int] = [0]

        class CountingRule:
            @property
            def code(self) -> str:
                return "FAKE01"

            def check(
                self,
                *,
                parse_result: ParseResult,
                config: PyGuardConfig,
            ) -> list[Diagnostic]:
                call_count[0] += 1
                return []

        monkeypatch.setattr(
            registry_mod,
            "_all_rules",
            lambda: [CountingRule()],
        )

        severities: dict[str, Severity] = {"FAKE01": Severity.ERROR}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)

        assert call_count[0] == 0
        assert result.diagnostics.error_count == 1
        assert result.diagnostics.sorted[0].code == "SYN001"

    def test_disabled_rules_not_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Rules set to OFF should not be included."""
        _write_file(tmp_path / "good.py", "x: int = 1\n")

        monkeypatch.setattr(registry_mod, "_all_rules", lambda: [FakeRule()])

        severities: dict[str, Severity] = {"FAKE01": Severity.OFF}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)

        assert result.files_checked == 1
        assert len(result.diagnostics) == 0

    def test_error_severity_sets_exit_code(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ERROR-severity diagnostics should cause exit code 1."""
        _write_file(tmp_path / "good.py", "x: int = 1\n")

        monkeypatch.setattr(registry_mod, "_all_rules", lambda: [FakeRule()])

        severities: dict[str, Severity] = {"FAKE01": Severity.ERROR}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)

        assert result.exit_code == 1

    def test_warn_severity_exit_code_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WARN-severity diagnostics should NOT cause exit code 1."""
        _write_file(tmp_path / "good.py", "x: int = 1\n")

        monkeypatch.setattr(registry_mod, "_all_rules", lambda: [FakeRule()])

        severities: dict[str, Severity] = {"FAKE01": Severity.WARN}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)

        assert result.exit_code == 0
