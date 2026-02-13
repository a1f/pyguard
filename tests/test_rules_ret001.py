"""Tests for RET001: Disallow heterogeneous tuple returns."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.ret001 import RET001Rule
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
    severities: dict[str, Severity] = {"RET001": severity}
    return PyGuardConfig(
        rules=RuleConfig(
            severities=MappingProxyType(severities),
        ),
    )


RULE: RET001Rule = RET001Rule()
CONFIG: PyGuardConfig = _make_config()


class TestRET001BasicDetection:
    def test_heterogeneous_tuple_return_flagged(self) -> None:
        code: str = (
            "def get_info() -> tuple[str, int, bool]:\n"
            '    return "Alice", 30, True\n'
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2
        assert diags[0].code == "RET001"
        assert "dataclass or NamedTuple" in diags[0].message

    def test_two_element_tuple_return_flagged(self) -> None:
        code: str = (
            "def divide(a: int, b: int) -> tuple[int, int]:\n"
            "    return a // b, a % b\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2

    def test_multiple_return_statements_all_flagged(self) -> None:
        code: str = (
            "def get_pair(x: int) -> tuple[int, str]:\n"
            "    if x > 0:\n"
            '        return x, "positive"\n'
            '    return 0, "zero"\n'
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2
        assert diags[0].location.line == 3
        assert diags[1].location.line == 4


class TestRET001Exemptions:
    def test_homogeneous_variadic_tuple_ok(self) -> None:
        code: str = (
            "def get_ids() -> tuple[int, ...]:\n"
            "    return (1, 2, 3)\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_no_return_annotation_ok(self) -> None:
        code: str = "def get_stuff():\n    return 1, 2\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_non_tuple_return_annotation_ok(self) -> None:
        code: str = "def get_name() -> str:\n    return 'Alice'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_dataclass_return_ok(self) -> None:
        code: str = (
            "class Info:\n"
            "    pass\n"
            "\n"
            "def get_info() -> Info:\n"
            "    return Info()\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_bare_tuple_annotation_ok(self) -> None:
        code: str = "def get_stuff() -> tuple:\n    return (1, 2)\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_single_element_tuple_ok(self) -> None:
        code: str = "def get_one() -> tuple[int]:\n    return (42,)\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_bare_return_not_flagged(self) -> None:
        code: str = (
            "def maybe() -> tuple[int, str]:\n"
            "    return\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestRET001AsyncAndNested:
    def test_async_function_flagged(self) -> None:
        code: str = (
            "async def fetch() -> tuple[int, str]:\n"
            '    return 200, "OK"\n'
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2

    def test_nested_function_return_not_flagged(self) -> None:
        """Return statements in nested functions should not be flagged by the outer function."""
        code: str = (
            "def outer() -> tuple[int, str]:\n"
            "    def inner() -> str:\n"
            '        return "hello"\n'
            '    return 1, inner()\n'
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 4

    def test_nested_function_with_own_tuple_return(self) -> None:
        """Nested function with its own heterogeneous tuple return should be flagged separately."""
        code: str = (
            "def outer() -> str:\n"
            "    def inner() -> tuple[int, str]:\n"
            '        return 1, "hello"\n'
            "    return str(inner())\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 3

    def test_method_in_class(self) -> None:
        code: str = (
            "class Service:\n"
            "    def get_pair(self) -> tuple[str, int]:\n"
            '        return "name", 42\n'
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 3


class TestRET001Metadata:
    def test_severity_from_config(self) -> None:
        config: PyGuardConfig = _make_config(severity=Severity.ERROR)
        code: str = "def f() -> tuple[int, str]:\n    return 1, 'a'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.ERROR

    def test_code_is_ret001(self) -> None:
        code: str = "def f() -> tuple[int, str]:\n    return 1, 'a'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].code == "RET001"

    def test_source_line_captured(self) -> None:
        code: str = "def f() -> tuple[int, str]:\n    return 1, 'a'\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "    return 1, 'a'"

    def test_rule_code_property(self) -> None:
        assert RULE.code == "RET001"

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
