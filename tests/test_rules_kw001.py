"""Tests for KW001: Require keyword-only parameters."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.kw001 import KW001Rule
from pyguard.types import KW001Options, PyGuardConfig, RuleConfig


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
    min_params: int = 2,
    exempt_dunder: bool = True,
    exempt_private: bool = True,
    exempt_overrides: bool = True,
) -> PyGuardConfig:
    severities: dict[str, Severity] = {"KW001": severity}
    return PyGuardConfig(
        rules=RuleConfig(
            severities=MappingProxyType(severities),
            kw001=KW001Options(
                min_params=min_params,
                exempt_dunder=exempt_dunder,
                exempt_private=exempt_private,
                exempt_overrides=exempt_overrides,
            ),
        ),
    )


RULE: KW001Rule = KW001Rule()
CONFIG: PyGuardConfig = _make_config()


class TestKW001BasicDetection:
    def test_public_function_multiple_params_flagged(self) -> None:
        result: ParseResult = _make_parse_result(
            "def create_user(name: str, email: str, age: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].code == "KW001"
        assert "create_user" in diags[0].message
        assert "Function" in diags[0].message

    def test_function_with_star_separator_clean(self) -> None:
        result: ParseResult = _make_parse_result(
            "def create_user(*, name: str, email: str) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_function_with_star_args_clean(self) -> None:
        result: ParseResult = _make_parse_result(
            "def func(*args: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_function_with_args_and_kwonly_clean(self) -> None:
        result: ParseResult = _make_parse_result(
            "def func(a: int, *args: int, key: str) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_single_param_exempt(self) -> None:
        result: ParseResult = _make_parse_result(
            "def get_user(user_id: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_no_params_exempt(self) -> None:
        result: ParseResult = _make_parse_result(
            "def noop() -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_exactly_min_params_flagged(self) -> None:
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestKW001Exemptions:
    def test_dunder_method_exempt(self) -> None:
        code: str = (
            "class Point:\n"
            "    def __init__(self, x: int, y: int) -> None:\n"
            "        self.x = x\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_dunder_not_exempt_when_disabled(self) -> None:
        config: PyGuardConfig = _make_config(exempt_dunder=False)
        code: str = (
            "class Point:\n"
            "    def __init__(self, x: int, y: int) -> None:\n"
            "        self.x = x\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 1

    def test_private_function_exempt(self) -> None:
        result: ParseResult = _make_parse_result(
            "def _internal_helper(a: int, b: int, c: int) -> int:\n    return a + b + c\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_private_not_exempt_when_disabled(self) -> None:
        config: PyGuardConfig = _make_config(exempt_private=False)
        result: ParseResult = _make_parse_result(
            "def _helper(a: int, b: int) -> int:\n    return a + b\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 1

    def test_override_decorated_exempt(self) -> None:
        code: str = (
            "class Child:\n"
            "    @override\n"
            "    def process(self, a: int, b: int) -> None:\n"
            "        pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_override_not_exempt_when_disabled(self) -> None:
        config: PyGuardConfig = _make_config(exempt_overrides=False)
        code: str = (
            "class Child:\n"
            "    @override\n"
            "    def process(self, a: int, b: int) -> None:\n"
            "        pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 1


class TestKW001Methods:
    def test_method_self_plus_one_param_exempt(self) -> None:
        code: str = (
            "class Calculator:\n"
            "    def double(self, value: int) -> int:\n"
            "        return value * 2\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_method_self_plus_multiple_params_flagged(self) -> None:
        code: str = (
            "class Calculator:\n"
            "    def compute(self, a: int, b: int, op: str) -> int:\n"
            "        return a + b\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert "Method" in diags[0].message
        assert "compute" in diags[0].message

    def test_classmethod_cls_plus_one_param_exempt(self) -> None:
        code: str = (
            "class Factory:\n"
            "    @classmethod\n"
            "    def create(cls, name: str) -> None:\n"
            "        pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_classmethod_cls_plus_multiple_params_flagged(self) -> None:
        code: str = (
            "class Factory:\n"
            "    @classmethod\n"
            "    def create(cls, name: str, value: int) -> None:\n"
            "        pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_staticmethod_multiple_params_flagged(self) -> None:
        code: str = (
            "class Util:\n"
            "    @staticmethod\n"
            "    def add(a: int, b: int) -> int:\n"
            "        return a + b\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestKW001Config:
    def test_min_params_3(self) -> None:
        config: PyGuardConfig = _make_config(min_params=3)
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags == []

    def test_min_params_3_with_3_params_flagged(self) -> None:
        config: PyGuardConfig = _make_config(min_params=3)
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int, c: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 1

    def test_severity_from_config(self) -> None:
        config: PyGuardConfig = _make_config(severity=Severity.ERROR)
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.ERROR


class TestKW001AsyncAndNested:
    def test_async_function_flagged(self) -> None:
        result: ParseResult = _make_parse_result(
            "async def fetch(url: str, timeout: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_nested_function_flagged(self) -> None:
        code: str = (
            "def outer() -> None:\n"
            "    def inner(a: int, b: int) -> int:\n"
            "        return a + b\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2


class TestKW001Metadata:
    def test_code_is_kw001(self) -> None:
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].code == "KW001"

    def test_source_line_captured(self) -> None:
        result: ParseResult = _make_parse_result(
            "def func(a: int, b: int) -> None:\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "def func(a: int, b: int) -> None:"

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
