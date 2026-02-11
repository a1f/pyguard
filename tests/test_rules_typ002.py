"""Tests for TYP002: Missing function return annotations."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.typ002 import TYP002Rule
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


RULE: TYP002Rule = TYP002Rule()
CONFIG: PyGuardConfig = PyGuardConfig()


class TestTYP002BasicDetection:
    def test_missing_return_annotation(self) -> None:
        result: ParseResult = _make_parse_result("def get_value():\n    return 42\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing return type annotation for function 'get_value'"
        assert diags[0].location.line == 1

    def test_annotated_no_diagnostics(self) -> None:
        result: ParseResult = _make_parse_result(
            "def calc(x: int) -> int:\n    return x\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_none_return_annotated(self) -> None:
        result: ParseResult = _make_parse_result(
            "def noop() -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_no_params_still_checked(self) -> None:
        result: ParseResult = _make_parse_result("def f():\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestTYP002AsyncAndNested:
    def test_async_function(self) -> None:
        result: ParseResult = _make_parse_result(
            "async def fetch():\n    return {}\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing return type annotation for function 'fetch'"

    def test_nested_function(self) -> None:
        code: str = "def outer() -> int:\n    def inner():\n        return 5\n    return inner()\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing return type annotation for function 'inner'"
        assert diags[0].location.line == 2

    def test_multiple_functions(self) -> None:
        code: str = "def a():\n    pass\ndef b():\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2


class TestTYP002DunderExemption:
    def test_init_exempted(self) -> None:
        code: str = "class C:\n    def __init__(self, x: int):\n        self.x = x\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_str_exempted(self) -> None:
        code: str = "class C:\n    def __str__(self):\n        return ''\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_repr_exempted(self) -> None:
        code: str = "class C:\n    def __repr__(self):\n        return ''\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_regular_method_not_exempted(self) -> None:
        code: str = "class C:\n    def method(self):\n        pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestTYP002Lambda:
    def test_lambda_not_flagged(self) -> None:
        result: ParseResult = _make_parse_result("double = lambda x: x * 2\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestTYP002Metadata:
    def test_severity_from_config(self) -> None:
        severities: dict[str, Severity] = {"TYP002": Severity.WARN}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        result: ParseResult = _make_parse_result("def f():\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.WARN

    def test_code_is_typ002(self) -> None:
        result: ParseResult = _make_parse_result("def f():\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].code == "TYP002"

    def test_source_line_captured(self) -> None:
        result: ParseResult = _make_parse_result("def f():\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "def f():"

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
