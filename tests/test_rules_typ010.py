"""Tests for TYP010: Disallow legacy typing syntax."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from types import MappingProxyType

from pyguard.constants import Severity
from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.typ010 import TYP010Rule
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


RULE: TYP010Rule = TYP010Rule()
CONFIG: PyGuardConfig = PyGuardConfig()


class TestTYP010BasicDetection:
    def test_optional_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Optional

            def f(x: int) -> Optional[str]:
                return None
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'str | None' instead of 'Optional[str]'"
        assert diags[0].location.line == 3

    def test_union_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Union

            def f(x: Union[str, int]) -> str:
                return str(x)
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'str | int' instead of 'Union[str, int]'"

    def test_list_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            def f() -> List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'list[str]' instead of 'List[str]'"

    def test_dict_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Dict

            def f() -> Dict[str, int]:
                return {}
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'dict[str, int]' instead of 'Dict[str, int]'"

    def test_tuple_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Tuple

            def f() -> Tuple[int, int]:
                return (0, 0)
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'tuple[int, int]' instead of 'Tuple[int, int]'"

    def test_set_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Set

            def f() -> Set[str]:
                return set()
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'set[str]' instead of 'Set[str]'"

    def test_frozenset_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import FrozenSet

            def f() -> FrozenSet[int]:
                return frozenset()
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'frozenset[int]' instead of 'FrozenSet[int]'"

    def test_type_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Type

            def f() -> Type[str]:
                return str
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'type[str]' instead of 'Type[str]'"


class TestTYP010NestedTypes:
    def test_nested_legacy_single_diagnostic(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Dict, List, Optional

            def f() -> Optional[Dict[str, List[int]]]:
                return None
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == (
            "Use 'dict[str, list[int]] | None' instead of "
            "'Optional[Dict[str, List[int]]]'"
        )

    def test_inner_legacy_in_modern_outer(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Dict

            def f() -> list[Dict[str, int]]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'dict[str, int]' instead of 'Dict[str, int]'"


class TestTYP010MultipleAnnotations:
    def test_multiple_params_each_flagged(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List, Dict

            def f(a: List[str], b: Dict[str, int]) -> None:
                pass
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2
        msgs: list[str] = [d.message for d in diags]
        assert "Use 'list[str]' instead of 'List[str]'" in msgs
        assert "Use 'dict[str, int]' instead of 'Dict[str, int]'" in msgs

    def test_params_and_return(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List, Optional

            def f(items: List[str]) -> Optional[str]:
                return None
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2


class TestTYP010VariableAnnotations:
    def test_variable_annotation_detected(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            ITEMS: List[str] = []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'list[str]' instead of 'List[str]'"

    def test_class_attribute_annotation(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import Optional

            class Config:
                name: Optional[str] = None
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestTYP010ImportTracking:
    def test_no_import_no_diagnostic(self) -> None:
        """Names that aren't imported from typing should not be flagged."""
        code: str = textwrap.dedent("""\
            class Optional:
                pass

            def f() -> Optional[str]:
                return None
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_typing_attribute_detected(self) -> None:
        code: str = textwrap.dedent("""\
            import typing

            def f() -> typing.List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1
        assert diags[0].message == "Use 'list[str]' instead of 'typing.List[str]'"

    def test_aliased_import(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List as L

            def f() -> L[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1


class TestTYP010ModernSyntaxOK:
    def test_builtin_generics_no_diagnostic(self) -> None:
        code: str = textwrap.dedent("""\
            def f() -> list[str]:
                return []

            def g() -> dict[str, int]:
                return {}
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_pipe_union_no_diagnostic(self) -> None:
        code: str = textwrap.dedent("""\
            def f() -> str | None:
                return None

            def g(x: int | str) -> str:
                return str(x)
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []

    def test_non_legacy_typing_ok(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import TypeVar, Protocol, Callable

            T = TypeVar("T")

            class Handler(Protocol):
                def handle(self, func: Callable[[int], int]) -> T:
                    ...
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags == []


class TestTYP010AsyncAndSpecialCases:
    def test_async_function(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            async def f() -> List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 1

    def test_args_kwargs_annotations(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            def f(*args: List[str], **kwargs: List[int]) -> None:
                pass
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert len(diags) == 2


class TestTYP010Metadata:
    def test_severity_from_config(self) -> None:
        severities: dict[str, Severity] = {"TYP010": Severity.WARN}
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(severities=MappingProxyType(severities)),
        )
        code: str = textwrap.dedent("""\
            from typing import List

            def f() -> List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=config)
        assert diags[0].severity == Severity.WARN

    def test_code_is_typ010(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            def f() -> List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].code == "TYP010"

    def test_source_line_captured(self) -> None:
        code: str = textwrap.dedent("""\
            from typing import List

            def f() -> List[str]:
                return []
        """)
        result: ParseResult = _make_parse_result(code)
        diags: list[Diagnostic] = RULE.check(parse_result=result, config=CONFIG)
        assert diags[0].source_line == "def f() -> List[str]:"

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
