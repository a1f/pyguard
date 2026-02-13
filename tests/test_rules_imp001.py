"""Tests for IMP001 rule: Disallow imports inside function bodies."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.imp001 import IMP001Rule
from pyguard.types import PyGuardConfig


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


def _check(code: str) -> list[Diagnostic]:
    rule: IMP001Rule = IMP001Rule()
    return rule.check(parse_result=_make_parse_result(code), config=PyGuardConfig())


class TestIMP001BasicDetection:
    def test_import_in_function(self) -> None:
        diags: list[Diagnostic] = _check("def f() -> None:\n    import json\n")
        assert len(diags) == 1
        assert diags[0].code == "IMP001"
        assert diags[0].location.line == 2
        assert "'json'" in diags[0].message

    def test_from_import_in_function(self) -> None:
        diags: list[Diagnostic] = _check(
            "def f() -> None:\n    from pathlib import Path\n"
        )
        assert len(diags) == 1
        assert "'pathlib.Path'" in diags[0].message

    def test_multiple_imports(self) -> None:
        code: str = (
            "def f() -> None:\n"
            "    import json\n"
            "    import re\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert len(diags) == 2
        assert diags[0].location.line == 2
        assert diags[1].location.line == 3

    def test_nested_function(self) -> None:
        code: str = (
            "def outer() -> None:\n"
            "    def inner() -> None:\n"
            "        import os\n"
            "    inner()\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert len(diags) == 1
        assert "'os'" in diags[0].message

    def test_async_function(self) -> None:
        diags: list[Diagnostic] = _check(
            "async def f() -> None:\n    import json\n"
        )
        assert len(diags) == 1

    def test_method_import(self) -> None:
        code: str = (
            "class C:\n"
            "    def m(self) -> None:\n"
            "        import json\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert len(diags) == 1


class TestIMP001NoFalsePositives:
    def test_top_level_import_ok(self) -> None:
        diags: list[Diagnostic] = _check("import json\n")
        assert diags == []

    def test_top_level_from_import_ok(self) -> None:
        diags: list[Diagnostic] = _check("from pathlib import Path\n")
        assert diags == []

    def test_class_level_import_ok(self) -> None:
        code: str = "class C:\n    import json\n"
        diags: list[Diagnostic] = _check(code)
        assert diags == []


class TestIMP001Exemptions:
    def test_type_checking_exempt(self) -> None:
        code: str = (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from some_module import SomeType\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []

    def test_typing_type_checking_exempt(self) -> None:
        code: str = (
            "import typing\n"
            "if typing.TYPE_CHECKING:\n"
            "    from some_module import SomeType\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []

    def test_try_except_import_error_exempt(self) -> None:
        code: str = (
            "def f() -> None:\n"
            "    try:\n"
            "        import ujson as json\n"
            "    except ImportError:\n"
            "        import json\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []

    def test_try_except_module_not_found_exempt(self) -> None:
        code: str = (
            "def f() -> None:\n"
            "    try:\n"
            "        import ujson\n"
            "    except ModuleNotFoundError:\n"
            "        import json\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []

    def test_bare_except_exempt(self) -> None:
        code: str = (
            "def f() -> None:\n"
            "    try:\n"
            "        import ujson\n"
            "    except:\n"
            "        import json\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []

    def test_try_except_non_import_error_not_exempt(self) -> None:
        code: str = (
            "def f() -> None:\n"
            "    try:\n"
            "        import json\n"
            "    except ValueError:\n"
            "        pass\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert len(diags) == 1

    def test_type_checking_in_function_exempt(self) -> None:
        code: str = (
            "from typing import TYPE_CHECKING\n"
            "def f() -> None:\n"
            "    if TYPE_CHECKING:\n"
            "        from some_module import SomeType\n"
        )
        diags: list[Diagnostic] = _check(code)
        assert diags == []


class TestIMP001SyntaxError:
    def test_syntax_error_returns_empty(self) -> None:
        rule: IMP001Rule = IMP001Rule()
        pr: ParseResult = ParseResult(
            file=Path("test.py"),
            tree=None,
            source="def f(\n",
            source_lines=("def f(",),
            syntax_error=None,
        )
        assert rule.check(parse_result=pr, config=PyGuardConfig()) == []
