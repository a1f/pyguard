"""Tests for EXP002: Enforce __all__ or explicit re-export policy."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.exp002 import EXP002Rule
from pyguard.types import PyGuardConfig, RuleConfig


def _make_parse_result(code: str) -> ParseResult:
    file: Path = Path("test.py")
    source_lines: tuple[str, ...] = tuple(code.splitlines())
    tree: ast.Module = ast.parse(code, filename=str(file))
    return ParseResult(
        file=file,
        tree=tree,
        source=code,
        source_lines=source_lines,
        syntax_error=None,
    )


def _make_config(
    *,
    severity: Severity = Severity.WARN,
) -> PyGuardConfig:
    severities: dict[str, Severity] = {"EXP002": severity}
    return PyGuardConfig(
        rules=RuleConfig(
            severities=MappingProxyType(severities),
        ),
    )


RULE: EXP002Rule = EXP002Rule()
CONFIG: PyGuardConfig = _make_config()


class TestEXP002BasicDetection:
    def test_public_function_no_all_flagged(self) -> None:
        code: str = "def greet() -> str:\n    return 'hello'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 1
        assert diags[0].code == "EXP002"
        assert "__all__" in diags[0].message

    def test_public_class_no_all_flagged(self) -> None:
        code: str = "class Service:\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_public_variable_no_all_flagged(self) -> None:
        code: str = "MAX_RETRIES = 3\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_public_annotated_variable_no_all_flagged(self) -> None:
        code: str = "MAX_RETRIES: int = 3\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_multiple_public_symbols_single_diagnostic(self) -> None:
        code: str = (
            "def func_a() -> None:\n"
            "    pass\n"
            "\n"
            "def func_b() -> None:\n"
            "    pass\n"
            "\n"
            "class MyClass:\n"
            "    pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_async_public_function_flagged(self) -> None:
        code: str = "async def fetch() -> None:\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestEXP002AllDefined:
    def test_all_defined_ok(self) -> None:
        code: str = (
            '__all__ = ["greet"]\n'
            "\n"
            "def greet() -> str:\n"
            "    return 'hello'\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_annotated_all_ok(self) -> None:
        code: str = (
            '__all__: list[str] = ["greet"]\n'
            "\n"
            "def greet() -> str:\n"
            "    return 'hello'\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_augmented_all_ok(self) -> None:
        code: str = (
            '__all__ = ["a"]\n'
            '__all__ += ["b"]\n'
            "\n"
            "def a() -> None:\n"
            "    pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestEXP002NoPublicSymbols:
    def test_only_private_functions_ok(self) -> None:
        code: str = (
            "def _helper() -> None:\n"
            "    pass\n"
            "\n"
            "def _internal() -> int:\n"
            "    return 42\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_only_private_class_ok(self) -> None:
        code: str = "class _Internal:\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_only_private_variables_ok(self) -> None:
        code: str = "_secret = 42\n_flag: bool = True\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_empty_module_ok(self) -> None:
        code: str = "# empty module\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_dunder_variable_not_public(self) -> None:
        code: str = '__version__ = "1.0"\n'
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestEXP002Metadata:
    def test_severity_from_config(self) -> None:
        config: PyGuardConfig = _make_config(severity=Severity.ERROR)
        code: str = "def greet() -> str:\n    return 'hi'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.ERROR

    def test_rule_code_property(self) -> None:
        assert RULE.code == "EXP002"

    def test_source_line_captured(self) -> None:
        code: str = "def greet() -> str:\n    return 'hi'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "def greet() -> str:"

    def test_none_tree_returns_empty(self) -> None:
        result: ParseResult = ParseResult(
            file=Path("test.py"),
            tree=None,
            source="",
            source_lines=(),
            syntax_error=None,
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []
