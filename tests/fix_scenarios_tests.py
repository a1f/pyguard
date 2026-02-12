"""
Fix Scenarios Tests for PyGuard.

This module contains TDD test cases for the PyGuard autofix functionality.
Each test scenario validates that the fixer correctly transforms code
as defined in the DESIGN.md specification.

Test Structure:
- Each test has a descriptive docstring explaining the scenario
- input_code contains the original Python code to be fixed
- expected_output contains the expected code after applying the fix
- All tests are skipped until the corresponding feature is implemented

Fix categories:
- TYP010: Modern typing syntax upgrades (safe autofix)
- TYP002: Add -> None for trivial functions (safe autofix)
- IMP001: Move imports to top level (safe in simple cases)
"""

import difflib
import textwrap
from typing import Any

import pytest

from pyguard.fixers.typ002 import fix_missing_return_none
from pyguard.fixers.typ003 import fix_missing_variable_annotations
from pyguard.fixers.typ010 import fix_legacy_typing


# =============================================================================
# TYP010: Modern Typing Syntax Fixes
# =============================================================================


class TestTYP010ModernTypingSyntaxFix:
    """
    TYP010: Modern typing syntax autofix.

    This fixer transforms legacy typing constructs to modern Python 3.11+ syntax:
    - Optional[T] -> T | None
    - Union[A, B] -> A | B
    - List[T] -> list[T]
    - Dict[K, V] -> dict[K, V]
    - Tuple[T, ...] -> tuple[T, ...]
    - Set[T] -> set[T]
    - FrozenSet[T] -> frozenset[T]
    - Type[T] -> type[T]

    The fixer should:
    - Preserve formatting and comments where possible
    - Remove unused typing imports after transformation
    - Handle nested type expressions correctly
    """

    def test_fix_optional_to_union_syntax(self) -> None:
        """
        Scenario: Transform Optional[T] to T | None.

        The fixer should replace Optional[T] with T | None and
        remove the Optional import if no longer needed.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Optional

            def find_user(user_id: int) -> Optional[str]:
                return None
        ''')

        expected_output: str = textwrap.dedent('''\
            def find_user(user_id: int) -> str | None:
                return None
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_union_to_pipe_syntax(self) -> None:
        """
        Scenario: Transform Union[A, B] to A | B.

        The fixer should replace Union syntax with the pipe operator.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Union

            def parse(value: Union[str, int]) -> str:
                return str(value)
        ''')

        expected_output: str = textwrap.dedent('''\
            def parse(value: str | int) -> str:
                return str(value)
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_union_multiple_types(self) -> None:
        """
        Scenario: Transform Union with multiple types.

        Union with more than 2 types should be transformed to chained pipes.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Union

            def process(value: Union[str, int, float, None]) -> str:
                return str(value)
        ''')

        expected_output: str = textwrap.dedent('''\
            def process(value: str | int | float | None) -> str:
                return str(value)
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_list_to_builtin(self) -> None:
        """
        Scenario: Transform List[T] to list[T].

        The fixer should replace typing.List with builtin list.
        """
        input_code: str = textwrap.dedent('''\
            from typing import List

            def get_names() -> List[str]:
                return ["Alice", "Bob"]
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_names() -> list[str]:
                return ["Alice", "Bob"]
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_dict_to_builtin(self) -> None:
        """
        Scenario: Transform Dict[K, V] to dict[K, V].

        The fixer should replace typing.Dict with builtin dict.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Dict

            def get_config() -> Dict[str, int]:
                return {"timeout": 30, "retries": 3}
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_config() -> dict[str, int]:
                return {"timeout": 30, "retries": 3}
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_tuple_to_builtin(self) -> None:
        """
        Scenario: Transform Tuple[T, ...] to tuple[T, ...].

        The fixer should replace typing.Tuple with builtin tuple.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Tuple

            def get_coords() -> Tuple[int, int]:
                return (0, 0)
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_coords() -> tuple[int, int]:
                return (0, 0)
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_set_to_builtin(self) -> None:
        """
        Scenario: Transform Set[T] to set[T].

        The fixer should replace typing.Set with builtin set.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Set

            def get_unique_tags() -> Set[str]:
                return {"python", "typing"}
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_unique_tags() -> set[str]:
                return {"python", "typing"}
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_frozenset_to_builtin(self) -> None:
        """
        Scenario: Transform FrozenSet[T] to frozenset[T].

        The fixer should replace typing.FrozenSet with builtin frozenset.
        """
        input_code: str = textwrap.dedent('''\
            from typing import FrozenSet

            def get_constants() -> FrozenSet[int]:
                return frozenset({1, 2, 3})
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_constants() -> frozenset[int]:
                return frozenset({1, 2, 3})
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_type_to_builtin(self) -> None:
        """
        Scenario: Transform Type[T] to type[T].

        The fixer should replace typing.Type with builtin type.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Type

            def get_class() -> Type[str]:
                return str
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_class() -> type[str]:
                return str
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_nested_types(self) -> None:
        """
        Scenario: Transform nested legacy typing constructs.

        The fixer should handle deeply nested type expressions.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Dict, List, Optional

            def get_users() -> Optional[Dict[str, List[int]]]:
                return None
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_users() -> dict[str, list[int]] | None:
                return None
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_multiple_types_same_line(self) -> None:
        """
        Scenario: Multiple legacy types in function signature.

        All legacy types in a signature should be transformed.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Dict, List, Optional

            def process(items: List[str], config: Dict[str, int]) -> Optional[str]:
                return None
        ''')

        expected_output: str = textwrap.dedent('''\
            def process(items: list[str], config: dict[str, int]) -> str | None:
                return None
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_preserves_other_typing_imports(self) -> None:
        """
        Scenario: Preserve typing imports that are still needed.

        If other typing constructs are still used (TypeVar, Protocol, etc.),
        those imports should be preserved.
        """
        input_code: str = textwrap.dedent('''\
            from typing import List, TypeVar, Protocol

            T = TypeVar("T")

            class Processor(Protocol):
                def process(self, items: List[T]) -> T:
                    ...
        ''')

        expected_output: str = textwrap.dedent('''\
            from typing import TypeVar, Protocol

            T = TypeVar("T")

            class Processor(Protocol):
                def process(self, items: list[T]) -> T:
                    ...
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_parameter_annotations(self) -> None:
        """
        Scenario: Fix legacy types in parameter annotations.

        Legacy types in parameters should also be transformed.
        """
        input_code: str = textwrap.dedent('''\
            from typing import List, Dict

            def merge(a: List[int], b: Dict[str, List[int]]) -> None:
                pass
        ''')

        expected_output: str = textwrap.dedent('''\
            def merge(a: list[int], b: dict[str, list[int]]) -> None:
                pass
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_variable_annotations(self) -> None:
        """
        Scenario: Fix legacy types in variable annotations.

        Module-level and class-level variable annotations should be transformed.
        """
        input_code: str = textwrap.dedent('''\
            from typing import List, Optional

            ITEMS: List[str] = []
            CURRENT_USER: Optional[str] = None
        ''')

        expected_output: str = textwrap.dedent('''\
            ITEMS: list[str] = []
            CURRENT_USER: str | None = None
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_class_attributes(self) -> None:
        """
        Scenario: Fix legacy types in class attribute annotations.

        Class attribute annotations should be transformed.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Dict, List, Optional

            class Config:
                values: Dict[str, int]
                items: List[str]
                name: Optional[str]
        ''')

        expected_output: str = textwrap.dedent('''\
            class Config:
                values: dict[str, int]
                items: list[str]
                name: str | None
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output

    def test_fix_callable_preserved(self) -> None:
        """
        Scenario: Callable should not be transformed (no builtin equivalent).

        typing.Callable has no builtin equivalent and should be preserved.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Callable, List

            def apply(func: Callable[[int], int], items: List[int]) -> List[int]:
                return [func(x) for x in items]
        ''')

        expected_output: str = textwrap.dedent('''\
            from typing import Callable

            def apply(func: Callable[[int], int], items: list[int]) -> list[int]:
                return [func(x) for x in items]
        ''')

        actual_output: str = fix_legacy_typing(input_code)
        assert actual_output == expected_output


# =============================================================================
# TYP002: Add -> None for Trivial Functions Fix
# =============================================================================


class TestTYP002AddNoneReturnFix:
    """
    TYP002: Add -> None for trivial functions autofix.

    This is a conservative safe fix that adds -> None return annotation
    to functions that have no return statements (or only bare 'return').

    The fixer should NOT add -> None when:
    - The function has return statements with values
    - The function is a generator (has yield)
    - The function already has a return annotation
    """

    def test_fix_add_none_return_simple(self) -> None:
        """
        Scenario: Simple function with no return statement.

        A function that doesn't return anything should get -> None annotation.
        """
        input_code: str = textwrap.dedent('''\
            def log_message(message: str):
                print(message)
        ''')

        expected_output: str = textwrap.dedent('''\
            def log_message(message: str) -> None:
                print(message)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_fix_add_none_return_with_bare_return(self) -> None:
        """
        Scenario: Function with bare return statement.

        A function with only bare 'return' should get -> None annotation.
        """
        input_code: str = textwrap.dedent('''\
            def early_exit(condition: bool):
                if condition:
                    return
                print("continuing")
        ''')

        expected_output: str = textwrap.dedent('''\
            def early_exit(condition: bool) -> None:
                if condition:
                    return
                print("continuing")
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_no_fix_when_returns_value(self) -> None:
        """
        Scenario: Function with return value.

        Functions that return values should NOT be auto-fixed.
        The fixer cannot infer the correct return type.
        """
        input_code: str = textwrap.dedent('''\
            def get_value():
                return 42
        ''')

        # Expected: No change (or only lint, no fix)
        expected_output: str = textwrap.dedent('''\
            def get_value():
                return 42
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_no_fix_when_generator(self) -> None:
        """
        Scenario: Generator function.

        Generator functions should NOT be auto-fixed to -> None.
        """
        input_code: str = textwrap.dedent('''\
            def count_up(n: int):
                for i in range(n):
                    yield i
        ''')

        # Expected: No change (generators have complex return types)
        expected_output: str = textwrap.dedent('''\
            def count_up(n: int):
                for i in range(n):
                    yield i
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_no_fix_when_already_annotated(self) -> None:
        """
        Scenario: Function already has return annotation.

        Functions with existing annotations should not be modified.
        """
        input_code: str = textwrap.dedent('''\
            def process(data: str) -> None:
                print(data)
        ''')

        expected_output: str = textwrap.dedent('''\
            def process(data: str) -> None:
                print(data)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_fix_method_no_return(self) -> None:
        """
        Scenario: Method with no return statement.

        Methods should also get -> None annotation when appropriate.
        """
        input_code: str = textwrap.dedent('''\
            class Logger:
                def log(self, message: str):
                    print(message)
        ''')

        expected_output: str = textwrap.dedent('''\
            class Logger:
                def log(self, message: str) -> None:
                    print(message)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_fix_async_function_no_return(self) -> None:
        """
        Scenario: Async function with no return.

        Async functions without return should get -> None annotation.
        """
        input_code: str = textwrap.dedent('''\
            async def send_notification(user_id: int, message: str):
                await notify(user_id, message)
        ''')

        expected_output: str = textwrap.dedent('''\
            async def send_notification(user_id: int, message: str) -> None:
                await notify(user_id, message)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_fix_preserves_decorators(self) -> None:
        """
        Scenario: Decorated function with no return.

        The fixer should preserve decorators when adding -> None.
        """
        input_code: str = textwrap.dedent('''\
            @decorator
            @another_decorator
            def decorated_function(x: int):
                print(x)
        ''')

        expected_output: str = textwrap.dedent('''\
            @decorator
            @another_decorator
            def decorated_function(x: int) -> None:
                print(x)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output

    def test_fix_preserves_multiline_signature(self) -> None:
        """
        Scenario: Function with multiline signature.

        The fixer should correctly handle functions with parameters
        spanning multiple lines.
        """
        input_code: str = textwrap.dedent('''\
            def complex_function(
                param1: str,
                param2: int,
                param3: bool,
            ):
                print(param1, param2, param3)
        ''')

        expected_output: str = textwrap.dedent('''\
            def complex_function(
                param1: str,
                param2: int,
                param3: bool,
            ) -> None:
                print(param1, param2, param3)
        ''')

        actual_output: str = fix_missing_return_none(input_code)
        assert actual_output == expected_output


# =============================================================================
# TYP003: Add Variable Type Annotations Fix
# =============================================================================


class TestTYP003AddVariableAnnotationFix:
    """
    TYP003: Add type annotations for variables with inferable types.

    This is a conservative safe fix that adds type annotations to
    simple assignments when the type is unambiguously inferable from
    the assigned value (literals or builtin constructor calls).
    """

    # --- Literal inference ---

    def test_fix_int_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = 5
        ''')
        expected: str = textwrap.dedent('''\
            x: int = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_str_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            name = "hello"
        ''')
        expected: str = textwrap.dedent('''\
            name: str = "hello"
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_float_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            pi = 3.14
        ''')
        expected: str = textwrap.dedent('''\
            pi: float = 3.14
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_bool_literal_true(self) -> None:
        input_code: str = textwrap.dedent('''\
            flag = True
        ''')
        expected: str = textwrap.dedent('''\
            flag: bool = True
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_bool_literal_false(self) -> None:
        input_code: str = textwrap.dedent('''\
            active = False
        ''')
        expected: str = textwrap.dedent('''\
            active: bool = False
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_bytes_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            data = b"raw"
        ''')
        expected: str = textwrap.dedent('''\
            data: bytes = b"raw"
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_complex_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            z = 4j
        ''')
        expected: str = textwrap.dedent('''\
            z: complex = 4j
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Bool before int ordering ---

    def test_bool_not_int(self) -> None:
        """True/False must be inferred as bool, not int (bool subclasses int)."""
        input_code: str = textwrap.dedent('''\
            a = True
            b = False
        ''')
        expected: str = textwrap.dedent('''\
            a: bool = True
            b: bool = False
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Builtin constructor calls ---

    def test_fix_dict_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            d = dict()
        ''')
        expected: str = textwrap.dedent('''\
            d: dict = dict()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_list_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            items = list()
        ''')
        expected: str = textwrap.dedent('''\
            items: list = list()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_set_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            s = set()
        ''')
        expected: str = textwrap.dedent('''\
            s: set = set()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_int_constructor_with_arg(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = int("5")
        ''')
        expected: str = textwrap.dedent('''\
            x: int = int("5")
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_frozenset_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            fs = frozenset()
        ''')
        expected: str = textwrap.dedent('''\
            fs: frozenset = frozenset()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_tuple_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            t = tuple()
        ''')
        expected: str = textwrap.dedent('''\
            t: tuple = tuple()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_bytearray_constructor(self) -> None:
        input_code: str = textwrap.dedent('''\
            ba = bytearray()
        ''')
        expected: str = textwrap.dedent('''\
            ba: bytearray = bytearray()
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Multiple fixable assignments ---

    def test_fix_multiple_assignments(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = 5
            name = "hello"
            pi = 3.14
        ''')
        expected: str = textwrap.dedent('''\
            x: int = 5
            name: str = "hello"
            pi: float = 3.14
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Mixed fixable and unfixable ---

    def test_fix_mixed_fixable_and_unfixable(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = 5
            result = foo()
            name = "hello"
            items = [1, 2, 3]
        ''')
        expected: str = textwrap.dedent('''\
            x: int = 5
            result = foo()
            name: str = "hello"
            items = [1, 2, 3]
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Skip cases ---

    def test_skip_none_literal(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = None
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_ellipsis(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = ...
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_multi_target(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = y = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_tuple_unpack(self) -> None:
        input_code: str = textwrap.dedent('''\
            a, b = 1, 2
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_attribute_target(self) -> None:
        input_code: str = textwrap.dedent('''\
            self.x = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_subscript_target(self) -> None:
        input_code: str = textwrap.dedent('''\
            items[0] = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_underscore(self) -> None:
        input_code: str = textwrap.dedent('''\
            _ = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_unknown_call(self) -> None:
        input_code: str = textwrap.dedent('''\
            result = foo()
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_list_display(self) -> None:
        input_code: str = textwrap.dedent('''\
            items = [1, 2, 3]
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_dict_display(self) -> None:
        input_code: str = textwrap.dedent('''\
            d = {"a": 1}
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_binop(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = 1 + 2
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_skip_unaryop(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = -1
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code

    # --- Scope handling ---

    def test_fix_module_level(self) -> None:
        input_code: str = textwrap.dedent('''\
            MAX_RETRIES = 3
        ''')
        expected: str = textwrap.dedent('''\
            MAX_RETRIES: int = 3
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_class_level(self) -> None:
        input_code: str = textwrap.dedent('''\
            class Config:
                timeout = 30
                name = "default"
        ''')
        expected: str = textwrap.dedent('''\
            class Config:
                timeout: int = 30
                name: str = "default"
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_fix_function_level(self) -> None:
        input_code: str = textwrap.dedent('''\
            def process() -> None:
                count = 0
                label = "start"
        ''')
        expected: str = textwrap.dedent('''\
            def process() -> None:
                count: int = 0
                label: str = "start"
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Preserves existing code ---

    def test_preserves_indentation(self) -> None:
        input_code: str = textwrap.dedent('''\
            if True:
                x = 5
        ''')
        expected: str = textwrap.dedent('''\
            if True:
                x: int = 5
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_preserves_comments(self) -> None:
        input_code: str = textwrap.dedent('''\
            # This is a count
            count = 0  # start at zero
        ''')
        expected: str = textwrap.dedent('''\
            # This is a count
            count: int = 0  # start at zero
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    def test_preserves_existing_annotations(self) -> None:
        """Already-annotated variables should not be double-annotated."""
        input_code: str = textwrap.dedent('''\
            x: int = 5
            y = "hello"
        ''')
        expected: str = textwrap.dedent('''\
            x: int = 5
            y: str = "hello"
        ''')
        assert fix_missing_variable_annotations(input_code) == expected

    # --- Idempotency ---

    def test_idempotent(self) -> None:
        input_code: str = textwrap.dedent('''\
            x = 5
            name = "hello"
        ''')
        first_pass: str = fix_missing_variable_annotations(input_code)
        second_pass: str = fix_missing_variable_annotations(first_pass)
        assert first_pass == second_pass

    # --- Graceful handling ---

    def test_syntax_error_returns_source(self) -> None:
        input_code: str = "def f(\n"
        assert fix_missing_variable_annotations(input_code) == input_code

    def test_empty_source(self) -> None:
        assert fix_missing_variable_annotations("") == ""

    def test_no_assignments(self) -> None:
        input_code: str = textwrap.dedent('''\
            def greet() -> None:
                print("hello")
        ''')
        assert fix_missing_variable_annotations(input_code) == input_code


# =============================================================================
# IMP001: Move Imports to Top Level Fix
# =============================================================================


@pytest.mark.skip(reason="IMP001 fix not yet implemented")
class TestIMP001MoveImportsFix:
    """
    IMP001: Move imports to module level autofix.

    This is a LIMITED safe fix that moves simple import statements
    from function bodies to the module level.

    The fixer should ONLY auto-fix when:
    - The import is a simple 'import X' or 'from X import Y'
    - There are no name conflicts at module level
    - The import is not conditional

    The fixer should NOT auto-fix when:
    - Moving would cause circular imports
    - There's a name conflict at module level
    - The import is inside a try/except or conditional
    """

    def test_fix_simple_import_move(self) -> None:
        """
        Scenario: Simple import inside function.

        A simple import statement should be moved to module level.
        """
        input_code: str = textwrap.dedent('''\
            def process_json(data: str) -> dict[str, object]:
                import json
                return json.loads(data)
        ''')

        expected_output: str = textwrap.dedent('''\
            import json

            def process_json(data: str) -> dict[str, object]:
                return json.loads(data)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_fix_from_import_move(self) -> None:
        """
        Scenario: From import inside function.

        A from import should be moved to module level.
        """
        input_code: str = textwrap.dedent('''\
            def get_cwd() -> str:
                from pathlib import Path
                return str(Path.cwd())
        ''')

        expected_output: str = textwrap.dedent('''\
            from pathlib import Path

            def get_cwd() -> str:
                return str(Path.cwd())
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_fix_multiple_imports_same_function(self) -> None:
        """
        Scenario: Multiple imports in same function.

        All imports should be moved to module level.
        """
        input_code: str = textwrap.dedent('''\
            def complex_operation(data: str) -> str:
                import json
                import re
                parsed = json.loads(data)
                return re.sub(r"\\s+", " ", str(parsed))
        ''')

        expected_output: str = textwrap.dedent('''\
            import json
            import re

            def complex_operation(data: str) -> str:
                parsed = json.loads(data)
                return re.sub(r"\\s+", " ", str(parsed))
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_no_fix_with_existing_import(self) -> None:
        """
        Scenario: Import already exists at module level.

        When the import already exists at module level,
        just remove the local import without adding duplicate.
        """
        input_code: str = textwrap.dedent('''\
            import json

            def process_json(data: str) -> dict[str, object]:
                import json
                return json.loads(data)
        ''')

        expected_output: str = textwrap.dedent('''\
            import json

            def process_json(data: str) -> dict[str, object]:
                return json.loads(data)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_no_fix_conditional_import(self) -> None:
        """
        Scenario: Conditional import.

        Imports inside try/except blocks should NOT be auto-fixed
        as they may be for optional dependencies.
        """
        input_code: str = textwrap.dedent('''\
            def process(data: str) -> dict[str, object]:
                try:
                    import ujson as json
                except ImportError:
                    import json
                return json.loads(data)
        ''')

        # Expected: No change (conditional imports are complex)
        expected_output: str = textwrap.dedent('''\
            def process(data: str) -> dict[str, object]:
                try:
                    import ujson as json
                except ImportError:
                    import json
                return json.loads(data)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_fix_preserves_import_order(self) -> None:
        """
        Scenario: Preserve standard library import ordering.

        When moving imports, they should be added in the correct section
        (stdlib vs third-party vs local).
        """
        input_code: str = textwrap.dedent('''\
            from myapp.utils import helper

            def process(data: str) -> dict[str, object]:
                import json
                return json.loads(data)
        ''')

        expected_output: str = textwrap.dedent('''\
            import json

            from myapp.utils import helper

            def process(data: str) -> dict[str, object]:
                return json.loads(data)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"

    def test_fix_method_import(self) -> None:
        """
        Scenario: Import inside method.

        Imports inside methods should also be moved to module level.
        """
        input_code: str = textwrap.dedent('''\
            class DataProcessor:
                def process(self, data: str) -> dict[str, object]:
                    import json
                    return json.loads(data)
        ''')

        expected_output: str = textwrap.dedent('''\
            import json

            class DataProcessor:
                def process(self, data: str) -> dict[str, object]:
                    return json.loads(data)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - IMP001 fix pending"


# =============================================================================
# KW001: Add Keyword-Only Marker Fix
# =============================================================================


@pytest.mark.skip(reason="KW001 fix not yet implemented")
class TestKW001KeywordOnlyFix:
    """
    KW001: Add keyword-only marker autofix.

    This is an UNSAFE fix (lint-only by default) because changing a function
    signature to keyword-only will break existing call sites that use
    positional arguments.

    The fix is available in "rewrite assist" mode where call sites can
    also be updated within the repository.
    """

    def test_fix_add_star_separator(self) -> None:
        """
        Scenario: Add * separator to make parameters keyword-only.

        When fix is explicitly requested, add * after first parameter
        or at the beginning if all params should be keyword-only.
        """
        input_code: str = textwrap.dedent('''\
            def create_user(name: str, email: str, age: int) -> dict[str, str | int]:
                return {"name": name, "email": email, "age": age}
        ''')

        expected_output: str = textwrap.dedent('''\
            def create_user(*, name: str, email: str, age: int) -> dict[str, str | int]:
                return {"name": name, "email": email, "age": age}
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - KW001 fix pending"

    def test_fix_method_preserves_self(self) -> None:
        """
        Scenario: Method with self parameter.

        The * separator should come after self.
        """
        input_code: str = textwrap.dedent('''\
            class UserService:
                def create_user(self, name: str, email: str, age: int) -> dict[str, str | int]:
                    return {"name": name, "email": email, "age": age}
        ''')

        expected_output: str = textwrap.dedent('''\
            class UserService:
                def create_user(self, *, name: str, email: str, age: int) -> dict[str, str | int]:
                    return {"name": name, "email": email, "age": age}
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - KW001 fix pending"

    def test_fix_classmethod_preserves_cls(self) -> None:
        """
        Scenario: Class method with cls parameter.

        The * separator should come after cls.
        """
        input_code: str = textwrap.dedent('''\
            class Factory:
                @classmethod
                def create(cls, name: str, value: int) -> "Factory":
                    return cls()
        ''')

        expected_output: str = textwrap.dedent('''\
            class Factory:
                @classmethod
                def create(cls, *, name: str, value: int) -> "Factory":
                    return cls()
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - KW001 fix pending"


# =============================================================================
# Rewrite Assist Scenarios (Not Auto-fixed)
# =============================================================================


@pytest.mark.skip(reason="Rewrite assist not yet implemented")
class TestRewriteAssistScenarios:
    """
    Rewrite Assist Scenarios.

    These tests document complex refactoring scenarios that require
    "rewrite assist" mode. These are NOT auto-fixed but generate
    structured rewrite plans for agent or human review.

    The rewrite plan includes:
    - Suggested type/class definition
    - List of affected return statements
    - List of affected call sites (within repo)
    """

    def test_rewrite_tuple_return_to_dataclass(self) -> None:
        """
        Scenario: Convert tuple return to dataclass.

        The rewrite assist should suggest creating a dataclass
        and provide a plan for updating the function.
        """
        input_code: str = textwrap.dedent('''\
            def get_user_info(user_id: int) -> tuple[str, int, bool]:
                name = "Alice"
                age = 30
                active = True
                return name, age, active
        ''')

        expected_rewrite_plan: dict[str, Any] = {
            "rule": "RET001",
            "action": "rewrite_required",
            "suggestion": {
                "type": "dataclass",
                "name": "UserInfo",
                "fields": [
                    {"name": "name", "type": "str"},
                    {"name": "age", "type": "int"},
                    {"name": "active", "type": "bool"},
                ],
            },
            "affected_locations": [
                {"file": "<input>", "line": 5, "type": "return_statement"},
            ],
        }

        suggested_output: str = textwrap.dedent('''\
            from dataclasses import dataclass

            @dataclass(frozen=True, slots=True)
            class UserInfo:
                name: str
                age: int
                active: bool

            def get_user_info(user_id: int) -> UserInfo:
                name = "Alice"
                age = 30
                active = True
                return UserInfo(name=name, age=age, active=active)
        ''')

        _unused = (input_code, expected_rewrite_plan, suggested_output)
        assert False, "Test not implemented - rewrite assist pending"

    def test_rewrite_tuple_return_to_namedtuple(self) -> None:
        """
        Scenario: Convert tuple return to NamedTuple.

        Alternative suggestion using NamedTuple.
        """
        input_code: str = textwrap.dedent('''\
            def divide(a: int, b: int) -> tuple[int, int]:
                quotient = a // b
                remainder = a % b
                return quotient, remainder
        ''')

        suggested_output: str = textwrap.dedent('''\
            from typing import NamedTuple

            class DivisionResult(NamedTuple):
                quotient: int
                remainder: int

            def divide(a: int, b: int) -> DivisionResult:
                quotient = a // b
                remainder = a % b
                return DivisionResult(quotient=quotient, remainder=remainder)
        ''')

        _unused = (input_code, suggested_output)
        assert False, "Test not implemented - rewrite assist pending"


# =============================================================================
# Combined Fix Scenarios
# =============================================================================


@pytest.mark.skip(reason="Combined fixes not yet implemented")
class TestCombinedFixes:
    """
    Combined Fix Scenarios.

    These tests verify that multiple fixes can be applied together
    in a single pass without conflicts.
    """

    def test_fix_multiple_rules_same_file(self) -> None:
        """
        Scenario: Multiple fixable issues in same file.

        The fixer should handle multiple issues correctly.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Optional, List

            def process_items(items: List[str]) -> Optional[str]:
                import json
                if not items:
                    return None
                return json.dumps(items)

            def log(message: str):
                print(message)
        ''')

        expected_output: str = textwrap.dedent('''\
            import json

            def process_items(items: list[str]) -> str | None:
                if not items:
                    return None
                return json.dumps(items)

            def log(message: str) -> None:
                print(message)
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - combined fixes pending"

    def test_fix_preserves_comments(self) -> None:
        """
        Scenario: Fixes preserve comments.

        Comments should be preserved during transformations.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Optional

            # This function finds a user by ID
            def find_user(user_id: int) -> Optional[str]:
                # Returns None if not found
                return None
        ''')

        expected_output: str = textwrap.dedent('''\
            # This function finds a user by ID
            def find_user(user_id: int) -> str | None:
                # Returns None if not found
                return None
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - comment preservation pending"

    def test_fix_preserves_docstrings(self) -> None:
        """
        Scenario: Fixes preserve docstrings.

        Docstrings should be preserved during transformations.
        """
        input_code: str = textwrap.dedent('''\
            from typing import List

            def get_names() -> List[str]:
                """Return a list of names.

                Returns:
                    A list of string names.
                """
                return ["Alice", "Bob"]
        ''')

        expected_output: str = textwrap.dedent('''\
            def get_names() -> list[str]:
                """Return a list of names.

                Returns:
                    A list of string names.
                """
                return ["Alice", "Bob"]
        ''')

        _unused = (input_code, expected_output)
        assert False, "Test not implemented - docstring preservation pending"


# =============================================================================
# Fix Stability Tests
# =============================================================================


@pytest.mark.skip(reason="Fix stability tests not yet implemented")
class TestFixStability:
    """
    Fix Stability Tests.

    These tests verify that fixes are idempotent and stable.
    Applying the fixer twice should produce the same output.
    """

    def test_fix_idempotent(self) -> None:
        """
        Scenario: Applying fix twice produces same result.

        After one fix pass, running again should not change the code.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Optional, List

            def process(items: List[str]) -> Optional[str]:
                return items[0] if items else None
        ''')

        expected_after_first_pass: str = textwrap.dedent('''\
            def process(items: list[str]) -> str | None:
                return items[0] if items else None
        ''')

        # Second pass should produce identical output
        expected_after_second_pass: str = expected_after_first_pass

        _unused = (input_code, expected_after_first_pass, expected_after_second_pass)
        assert False, "Test not implemented - fix stability pending"

    def test_fix_stable_with_black(self) -> None:
        """
        Scenario: Fixed code remains stable after Black formatting.

        The fixed code should not change when formatted with Black.
        This ensures our fixes produce Black-compatible output.
        """
        input_code: str = textwrap.dedent('''\
            from typing import Optional

            def find_user(user_id: int) -> Optional[str]:
                return None
        ''')

        # After pyguard fix
        after_pyguard_fix: str = textwrap.dedent('''\
            def find_user(user_id: int) -> str | None:
                return None
        ''')

        # After Black (should be identical)
        after_black: str = after_pyguard_fix

        _unused = (input_code, after_pyguard_fix, after_black)
        assert False, "Test not implemented - Black stability pending"


# =============================================================================
# Test Utilities (to be implemented with the fixer)
# =============================================================================


def assert_code_equal(*, actual: str, expected: str) -> None:
    """
    Assert code equality with helpful diff output.

    This will be used when the fixer is implemented.
    """
    actual_lines: list[str] = actual.strip().splitlines()
    expected_lines: list[str] = expected.strip().splitlines()

    if actual_lines != expected_lines:
        diff = difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
        diff_text: str = "\n".join(diff)
        raise AssertionError(f"Code mismatch:\n{diff_text}")
