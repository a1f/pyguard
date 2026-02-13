"""Tests for KW001 fixer: Insert * separator in function signatures."""
from __future__ import annotations

import textwrap
from pathlib import Path

from pyguard.fixers.kw001 import FixResult, fix_keyword_only
from pyguard.types import PyGuardConfig


def _fix(source: str) -> str:
    """Fix a single source string with default config."""
    config: PyGuardConfig = PyGuardConfig()
    result: FixResult = fix_keyword_only(
        sources={Path("test.py"): source},
        config=config,
    )
    return result.sources[Path("test.py")]


class TestSignatureFixBasic:
    def test_insert_star_all_positional(self) -> None:
        source: str = "def f(a: int, b: int, c: int) -> None:\n    pass\n"
        assert _fix(source) == "def f(*, a: int, b: int, c: int) -> None:\n    pass\n"

    def test_insert_star_after_self(self) -> None:
        source: str = textwrap.dedent("""\
            class C:
                def method(self, a: int, b: int) -> None:
                    pass
        """)
        expected: str = textwrap.dedent("""\
            class C:
                def method(self, *, a: int, b: int) -> None:
                    pass
        """)
        assert _fix(source) == expected

    def test_insert_star_after_cls(self) -> None:
        source: str = textwrap.dedent("""\
            class Factory:
                @classmethod
                def create(cls, name: str, value: int) -> "Factory":
                    return cls()
        """)
        expected: str = textwrap.dedent("""\
            class Factory:
                @classmethod
                def create(cls, *, name: str, value: int) -> "Factory":
                    return cls()
        """)
        assert _fix(source) == expected

    def test_params_with_defaults(self) -> None:
        source: str = 'def greet(name: str, greeting: str = "Hello") -> str:\n    return "hi"\n'
        expected: str = 'def greet(*, name: str, greeting: str = "Hello") -> str:\n    return "hi"\n'
        assert _fix(source) == expected


class TestSignatureFixNoChange:
    def test_already_has_star_separator(self) -> None:
        source: str = "def f(*, a: int, b: int) -> None:\n    pass\n"
        assert _fix(source) == source

    def test_already_has_star_args(self) -> None:
        source: str = "def f(*args: int) -> None:\n    pass\n"
        assert _fix(source) == source

    def test_single_param_no_change(self) -> None:
        source: str = "def f(a: int) -> None:\n    pass\n"
        assert _fix(source) == source

    def test_no_params_no_change(self) -> None:
        source: str = "def f() -> None:\n    pass\n"
        assert _fix(source) == source

    def test_dunder_exempt(self) -> None:
        source: str = textwrap.dedent("""\
            class P:
                def __init__(self, x: int, y: int) -> None:
                    pass
        """)
        assert _fix(source) == source

    def test_private_exempt(self) -> None:
        source: str = "def _helper(a: int, b: int) -> int:\n    return a + b\n"
        assert _fix(source) == source

    def test_override_exempt(self) -> None:
        source: str = textwrap.dedent("""\
            class Child:
                @override
                def process(self, a: int, b: int) -> None:
                    pass
        """)
        assert _fix(source) == source


class TestSignatureFixMultipleFunctions:
    def test_fix_multiple_in_same_file(self) -> None:
        source: str = textwrap.dedent("""\
            def first(a: int, b: int) -> None:
                pass

            def second(x: str, y: str) -> None:
                pass
        """)
        expected: str = textwrap.dedent("""\
            def first(*, a: int, b: int) -> None:
                pass

            def second(*, x: str, y: str) -> None:
                pass
        """)
        assert _fix(source) == expected

    def test_fix_mixed_fixable_and_exempt(self) -> None:
        source: str = textwrap.dedent("""\
            def public(a: int, b: int) -> None:
                pass

            def _private(a: int, b: int) -> None:
                pass
        """)
        expected: str = textwrap.dedent("""\
            def public(*, a: int, b: int) -> None:
                pass

            def _private(a: int, b: int) -> None:
                pass
        """)
        assert _fix(source) == expected


class TestSignatureFixAsync:
    def test_async_function(self) -> None:
        source: str = "async def fetch(url: str, timeout: int) -> None:\n    pass\n"
        expected: str = "async def fetch(*, url: str, timeout: int) -> None:\n    pass\n"
        assert _fix(source) == expected


class TestSignatureFixMultiFile:
    def test_fix_across_multiple_files(self) -> None:
        config: PyGuardConfig = PyGuardConfig()
        sources: dict[Path, str] = {
            Path("a.py"): "def f(a: int, b: int) -> None:\n    pass\n",
            Path("b.py"): "def g(x: str, y: str) -> None:\n    pass\n",
        }
        result: FixResult = fix_keyword_only(sources=sources, config=config)
        assert result.sources[Path("a.py")] == "def f(*, a: int, b: int) -> None:\n    pass\n"
        assert result.sources[Path("b.py")] == "def g(*, x: str, y: str) -> None:\n    pass\n"


class TestSignatureFixEdgeCases:
    def test_syntax_error_returns_unchanged(self) -> None:
        source: str = "def f(a, b\n"
        assert _fix(source) == source

    def test_empty_source(self) -> None:
        source: str = ""
        assert _fix(source) == source

    def test_staticmethod_fixed(self) -> None:
        source: str = textwrap.dedent("""\
            class Util:
                @staticmethod
                def add(a: int, b: int) -> int:
                    return a + b
        """)
        expected: str = textwrap.dedent("""\
            class Util:
                @staticmethod
                def add(*, a: int, b: int) -> int:
                    return a + b
        """)
        assert _fix(source) == expected
