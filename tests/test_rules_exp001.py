"""Tests for EXP001: Structured return types must be module-level."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.exp001 import EXP001Rule
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
    severities: dict[str, Severity] = {"EXP001": severity}
    return PyGuardConfig(
        rules=RuleConfig(
            severities=MappingProxyType(severities),
        ),
    )


RULE: EXP001Rule = EXP001Rule()
CONFIG: PyGuardConfig = _make_config()


class TestEXP001BasicDetection:
    def test_decorated_class_inside_function_flagged(self) -> None:
        code: str = (
            "from dataclasses import dataclass\n"
            "\n"
            'def get_result() -> "Result":\n'
            "    @dataclass\n"
            "    class Result:\n"
            "        value: int\n"
            "    return Result(value=42)\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 4
        assert diags[0].code == "EXP001"
        assert "Result" in diags[0].message
        assert "module level" in diags[0].message

    def test_plain_class_inside_function_flagged(self) -> None:
        code: str = (
            'def get_info() -> "Info":\n'
            "    class Info:\n"
            "        name: str = ''\n"
            "    return Info()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2

    def test_string_annotation_detected(self) -> None:
        code: str = (
            'def get_data() -> "Data":\n'
            "    class Data:\n"
            "        x: int = 0\n"
            "    return Data()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert "Data" in diags[0].message

    def test_name_annotation_detected(self) -> None:
        code: str = (
            "class Result:\n"
            "    pass\n"
            "\n"
            "def outer() -> None:\n"
            "    def inner() -> Result:\n"
            "        class Result:\n"
            "            value: int = 0\n"
            "        return Result()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 6


class TestEXP001Exemptions:
    def test_module_level_class_ok(self) -> None:
        code: str = (
            "class Result:\n"
            "    value: int = 0\n"
            "\n"
            "def get_result() -> Result:\n"
            "    return Result()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_no_return_annotation_ok(self) -> None:
        code: str = (
            "def get_result():\n"
            "    class Result:\n"
            "        value: int = 0\n"
            "    return Result()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_class_name_does_not_match_return_type(self) -> None:
        code: str = (
            'def get_data() -> "Output":\n'
            "    class Helper:\n"
            "        pass\n"
            "    return Helper()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_complex_return_annotation_ignored(self) -> None:
        code: str = (
            "def get_items() -> list[int]:\n"
            "    class Items:\n"
            "        pass\n"
            "    return [1, 2]\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_builtin_return_type_ok(self) -> None:
        code: str = "def get_value() -> int:\n    return 42\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestEXP001AsyncAndNested:
    def test_async_function_flagged(self) -> None:
        code: str = (
            'async def fetch() -> "Response":\n'
            "    class Response:\n"
            "        status: int = 200\n"
            "    return Response()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_nested_function_checked_independently(self) -> None:
        code: str = (
            "def outer() -> int:\n"
            '    def inner() -> "Local":\n'
            "        class Local:\n"
            "            x: int = 0\n"
            "        return Local()\n"
            "    return 42\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 3

    def test_method_in_class_flagged(self) -> None:
        code: str = (
            "class Service:\n"
            '    def get_result(self) -> "Result":\n'
            "        class Result:\n"
            "            value: int = 0\n"
            "        return Result()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestEXP001Metadata:
    def test_severity_from_config(self) -> None:
        config: PyGuardConfig = _make_config(severity=Severity.ERROR)
        code: str = (
            'def f() -> "R":\n'
            "    class R:\n"
            "        pass\n"
            "    return R()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.ERROR

    def test_rule_code_property(self) -> None:
        assert RULE.code == "EXP001"

    def test_source_line_captured(self) -> None:
        code: str = (
            'def f() -> "R":\n'
            "    class R:\n"
            "        pass\n"
            "    return R()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "    class R:"

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
