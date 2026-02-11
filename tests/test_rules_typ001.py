"""Tests for TYP001: Missing function parameter annotations."""
from __future__ import annotations

import ast
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.typ001 import TYP001Rule
from pyguard.types import PyGuardConfig, RuleConfig, TYP001Options


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
    severity: Severity = Severity.ERROR,
    exempt_dunder: bool = True,
    exempt_self_cls: bool = True,
) -> PyGuardConfig:
    severities: dict[str, Severity] = {"TYP001": severity}
    return PyGuardConfig(
        rules=RuleConfig(
            severities=MappingProxyType(severities),
            typ001=TYP001Options(
                exempt_dunder=exempt_dunder,
                exempt_self_cls=exempt_self_cls,
            ),
        ),
    )


RULE: TYP001Rule = TYP001Rule()
CONFIG: PyGuardConfig = _make_config()


class TestTYP001BasicDetection:
    def test_missing_all_annotations(self) -> None:
        result: ParseResult = _make_parse_result("def add(x, y):\n    return x + y\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2
        assert diags[0].message == "Missing type annotation for parameter 'x'"
        assert diags[1].message == "Missing type annotation for parameter 'y'"
        assert diags[0].location.line == 1
        assert diags[1].location.line == 1

    def test_partial_annotations(self) -> None:
        result: ParseResult = _make_parse_result(
            "def process(x: int, y: str, z):\n    pass\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'z'"

    def test_fully_annotated_no_diagnostics(self) -> None:
        result: ParseResult = _make_parse_result(
            "def multiply(x: int, y: int) -> int:\n    return x * y\n"
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_default_value_still_flagged(self) -> None:
        result: ParseResult = _make_parse_result(
            'def greet(name="World"):\n    return f"Hello, {name}!"\n'
        )
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'name'"

    def test_no_params_no_diagnostics(self) -> None:
        result: ParseResult = _make_parse_result("def noop():\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestTYP001SelfClsExemption:
    def test_self_exempted(self) -> None:
        code: str = "class C:\n    def method(self, x):\n        pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'x'"

    def test_cls_exempted(self) -> None:
        code: str = (
            "class C:\n    @classmethod\n    def create(cls, name):\n        pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'name'"

    def test_self_cls_not_exempted_when_disabled(self) -> None:
        config: PyGuardConfig = _make_config(exempt_self_cls=False)
        code: str = "class C:\n    def method(self, x):\n        pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 2
        messages: list[str] = [d.message for d in diags]
        assert "Missing type annotation for parameter 'self'" in messages
        assert "Missing type annotation for parameter 'x'" in messages

    def test_self_not_exempted_in_free_function(self) -> None:
        code: str = "def func(self, x):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2


class TestTYP001DunderExemption:
    def test_dunder_exempted(self) -> None:
        code: str = "class C:\n    def __init__(self, x):\n        self.x = x\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_dunder_not_exempted_when_disabled(self) -> None:
        config: PyGuardConfig = _make_config(exempt_dunder=False)
        code: str = "class C:\n    def __init__(self, x):\n        self.x = x\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'x'"

    def test_single_underscore_not_dunder(self) -> None:
        code: str = "def _private(x):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_double_underscore_prefix_not_dunder(self) -> None:
        code: str = "def __mangled(x):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestTYP001ArgsKwargs:
    def test_args_kwargs_not_checked(self) -> None:
        code: str = "def func(*args, **kwargs):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_mixed_with_args_kwargs(self) -> None:
        code: str = "def func(x, *args, **kwargs):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'x'"


class TestTYP001AsyncAndNested:
    def test_async_function(self) -> None:
        code: str = "async def fetch(url):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'url'"

    def test_nested_function(self) -> None:
        code: str = "def outer() -> None:\n    def inner(x):\n        pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].location.line == 2

    def test_nested_method_in_class(self) -> None:
        code: str = (
            "class C:\n"
            "    def method(self) -> None:\n"
            "        def helper(x):\n"
            "            pass\n"
        )
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Missing type annotation for parameter 'x'"


class TestTYP001KwOnly:
    def test_kwonly_params_checked(self) -> None:
        code: str = "def func(*, key, value):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2

    def test_posonly_params_checked(self) -> None:
        code: str = "def func(x, y, /):\n    pass\n"
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2


class TestTYP001Metadata:
    def test_severity_from_config(self) -> None:
        config: PyGuardConfig = _make_config(severity=Severity.WARN)
        result: ParseResult = _make_parse_result("def f(x):\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.WARN

    def test_code_is_typ001(self) -> None:
        result: ParseResult = _make_parse_result("def f(x):\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].code == "TYP001"

    def test_source_line_captured(self) -> None:
        result: ParseResult = _make_parse_result("def f(x):\n    pass\n")
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "def f(x):"

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
