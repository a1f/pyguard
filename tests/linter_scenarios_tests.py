"""
Linter Scenarios Tests for PyGuard.

This module contains TDD test cases for the PyGuard linter functionality.
Each test scenario validates that the linter correctly detects style violations
as defined in the DESIGN.md specification.

Test Structure:
- Each test has a descriptive docstring explaining the scenario
- code_sample contains the Python code to be linted
- expected_diagnostics contains the expected (line, code, message) tuples
- All tests are skipped until the corresponding feature is implemented

Rules covered:
- TYP001: Missing function parameter annotations
- TYP002: Missing function return annotation
- TYP003: Missing variable annotation
- TYP010: Disallow legacy typing syntax
- KW001: Require keyword-only parameters
- RET001: Disallow heterogeneous tuple returns
- IMP001: Disallow imports inside function bodies
- EXP001: Structured return types must be module-level
- EXP002: Enforce __all__ or explicit re-export policy
"""

import ast
from pathlib import Path
from typing import NamedTuple

import pytest

from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.rules.imp001 import IMP001Rule
from pyguard.rules.kw001 import KW001Rule
from pyguard.rules.ret001 import RET001Rule
from pyguard.rules.typ001 import TYP001Rule
from pyguard.rules.typ002 import TYP002Rule
from pyguard.rules.typ003 import TYP003Rule
from pyguard.rules.typ010 import TYP010Rule
from pyguard.constants import AnnotationScope
from pyguard.types import PyGuardConfig, RuleConfig, TYP003Options


class ExpectedDiagnostic(NamedTuple):
    """Represents an expected diagnostic from the linter."""

    line: int
    code: str
    message: str


def _check_code(code: str, *, rule_code: str) -> list[Diagnostic]:
    """Parse code and run the specified rule, returning diagnostics."""
    file: Path = Path("scenario.py")
    source_lines: tuple[str, ...] = tuple(code.splitlines())
    tree: ast.Module = ast.parse(code, filename=str(file))
    parse_result: ParseResult = ParseResult(
        file=file,
        tree=tree,
        source=code,
        source_lines=source_lines,
        syntax_error=None,
    )
    config: PyGuardConfig = PyGuardConfig()
    rules: dict[str, object] = {
        "TYP001": TYP001Rule(),
        "TYP002": TYP002Rule(),
        "TYP003": TYP003Rule(),
        "TYP010": TYP010Rule(),
        "KW001": KW001Rule(),
        "IMP001": IMP001Rule(),
        "RET001": RET001Rule(),
    }
    rule: object = rules[rule_code]
    return rule.check(parse_result=parse_result, config=config)  # type: ignore[union-attr]


def _assert_diagnostics_match(
    actual: list[Diagnostic],
    expected: list[ExpectedDiagnostic],
) -> None:
    """Assert that actual diagnostics match expected (line, code, message)."""
    actual_tuples: list[tuple[int, str, str]] = [
        (d.location.line, d.code, d.message) for d in actual
    ]
    expected_tuples: list[tuple[int, str, str]] = [
        (e.line, e.code, e.message) for e in expected
    ]
    assert actual_tuples == expected_tuples


# =============================================================================
# TYP001: Missing function parameter annotations
# =============================================================================


class TestTYP001MissingParameterAnnotations:
    """
    TYP001: Missing function parameter annotations.

    This rule enforces that all function parameters must have type annotations.
    The linter should detect parameters without type hints and report them.

    Exemptions (configurable):
    - self/cls parameters in methods
    - *args and **kwargs (configurable)
    - dunder methods (configurable)
    - Protocol implementations (configurable)
    """

    def test_basic_missing_parameter_annotation(self) -> None:
        """
        Scenario: A simple function with unannotated parameters.

        The linter should flag each parameter that lacks a type annotation.
        In this case, both 'x' and 'y' are missing annotations.
        """
        code_sample: str = '''\
def add(x, y):
    return x + y
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP001",
                message="Missing type annotation for parameter 'x'",
            ),
            ExpectedDiagnostic(
                line=1,
                code="TYP001",
                message="Missing type annotation for parameter 'y'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_partial_parameter_annotations(self) -> None:
        """
        Scenario: Function with some annotated and some unannotated parameters.

        Only the unannotated parameter 'z' should be flagged.
        """
        code_sample: str = '''\
def process(x: int, y: str, z):
    return f"{x} {y} {z}"
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP001",
                message="Missing type annotation for parameter 'z'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_self_parameter_exempted(self) -> None:
        """
        Scenario: Method with 'self' parameter.

        The 'self' parameter should be exempted from annotation requirement,
        but other parameters should still be checked.
        """
        code_sample: str = '''\
class Calculator:
    def add(self, x, y):
        return x + y
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="TYP001",
                message="Missing type annotation for parameter 'x'",
            ),
            ExpectedDiagnostic(
                line=2,
                code="TYP001",
                message="Missing type annotation for parameter 'y'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_cls_parameter_exempted(self) -> None:
        """
        Scenario: Class method with 'cls' parameter.

        The 'cls' parameter should be exempted from annotation requirement.
        """
        code_sample: str = '''\
class Factory:
    @classmethod
    def create(cls, name):
        return cls(name)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP001",
                message="Missing type annotation for parameter 'name'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_default_values_still_need_annotations(self) -> None:
        """
        Scenario: Parameters with default values but no annotations.

        Even if a parameter has a default value, it still needs a type annotation.
        """
        code_sample: str = '''\
def greet(name="World"):
    return f"Hello, {name}!"
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP001",
                message="Missing type annotation for parameter 'name'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_fully_annotated_no_errors(self) -> None:
        """
        Scenario: Function with all parameters properly annotated.

        No diagnostics should be generated.
        """
        code_sample: str = '''\
def multiply(x: int, y: int) -> int:
    return x * y
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# TYP002: Missing function return annotation
# =============================================================================


class TestTYP002MissingReturnAnnotation:
    """
    TYP002: Missing function return annotation.

    This rule enforces that all functions must have return type annotations.
    The linter should detect functions without return type hints.

    Exemptions (configurable):
    - dunder methods like __init__, __str__ (configurable)
    - @override decorated methods (configurable)
    - Protocol implementations (configurable)
    """

    def test_basic_missing_return_annotation(self) -> None:
        """
        Scenario: Simple function without return annotation.

        The linter should flag the function for missing return type.
        """
        code_sample: str = '''\
def get_value():
    return 42
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP002",
                message="Missing return type annotation for function 'get_value'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_lambda_not_flagged(self) -> None:
        """
        Scenario: Lambda expressions.

        Lambda expressions cannot have annotations in Python syntax,
        so they should not be flagged by this rule.
        """
        code_sample: str = '''\
double = lambda x: x * 2
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_async_function_missing_return(self) -> None:
        """
        Scenario: Async function without return annotation.

        Async functions should also be checked for return annotations.
        """
        code_sample: str = '''\
async def fetch_data():
    return {"data": "value"}
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP002",
                message="Missing return type annotation for function 'fetch_data'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_nested_function_missing_return(self) -> None:
        """
        Scenario: Nested function without return annotation.

        Inner functions should also be checked.
        """
        code_sample: str = '''\
def outer() -> int:
    def inner():
        return 5
    return inner()
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="TYP002",
                message="Missing return type annotation for function 'inner'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_dunder_init_exempted(self) -> None:
        """
        Scenario: __init__ method without explicit return annotation.

        The __init__ method implicitly returns None and should be exempted
        (configurable behavior).
        """
        code_sample: str = '''\
class MyClass:
    def __init__(self, value: int):
        self.value = value
'''
        # By default, __init__ should be exempted
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_properly_annotated_no_errors(self) -> None:
        """
        Scenario: Function with proper return annotation.

        No diagnostics should be generated.
        """
        code_sample: str = '''\
def calculate(x: int, y: int) -> int:
    return x + y
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP002")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# TYP003: Missing variable annotation
# =============================================================================


class TestTYP003MissingVariableAnnotation:
    """
    TYP003: Missing variable annotation.

    This rule enforces type annotations on variable assignments.
    Scope is configurable: module-level only vs all assignments.

    Default behavior: module-level only (to reduce noise)

    Exemptions:
    - Underscore variables (_ = ...)
    - Comprehension targets
    - For-loop targets
    - Unpacking assignments
    """

    def test_module_level_missing_annotation(self) -> None:
        """
        Scenario: Module-level variable without annotation.

        Top-level variables should have type annotations.
        """
        code_sample: str = '''\
MAX_RETRIES = 3
TIMEOUT = 30.0
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="TYP003",
                message="Missing type annotation for module-level variable 'MAX_RETRIES'",
            ),
            ExpectedDiagnostic(
                line=2,
                code="TYP003",
                message="Missing type annotation for module-level variable 'TIMEOUT'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP003")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_module_level_with_annotation_ok(self) -> None:
        """
        Scenario: Module-level variable with proper annotation.

        No diagnostics should be generated.
        """
        code_sample: str = '''\
MAX_RETRIES: int = 3
TIMEOUT: float = 30.0
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP003")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_underscore_variable_exempted(self) -> None:
        """
        Scenario: Underscore variable assignment.

        The _ variable is commonly used to discard values and should
        be exempted from annotation requirements.
        """
        code_sample: str = '''\
_ = some_function_with_side_effects()
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP003")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_for_loop_target_exempted(self) -> None:
        """
        Scenario: For-loop iteration variable.

        Loop variables should be exempted from annotation requirements.
        """
        code_sample: str = '''\
items: list[int] = [1, 2, 3]
for item in items:
    print(item)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP003")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_comprehension_target_exempted(self) -> None:
        """
        Scenario: List comprehension iteration variable.

        Comprehension variables should be exempted.
        """
        code_sample: str = '''\
squares: list[int] = [x * x for x in range(10)]
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP003")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_class_level_variable(self) -> None:
        """
        Scenario: Class-level variable without annotation.

        Class attributes should also be annotated (configurable scope).
        """
        code_sample: str = '''\
class Config:
    debug = False
    max_connections = 10
'''
        # When scope includes "class"
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="TYP003",
                message="Missing type annotation for class variable 'debug'",
            ),
            ExpectedDiagnostic(
                line=3,
                code="TYP003",
                message="Missing type annotation for class variable 'max_connections'",
            ),
        ]

        file: Path = Path("scenario.py")
        source_lines: tuple[str, ...] = tuple(code_sample.splitlines())
        tree: ast.Module = ast.parse(code_sample, filename=str(file))
        parse_result: ParseResult = ParseResult(
            file=file,
            tree=tree,
            source=code_sample,
            source_lines=source_lines,
            syntax_error=None,
        )
        config: PyGuardConfig = PyGuardConfig(
            rules=RuleConfig(
                typ003=TYP003Options(
                    scope=frozenset({AnnotationScope.MODULE, AnnotationScope.CLASS}),
                ),
            ),
        )
        diagnostics: list[Diagnostic] = TYP003Rule().check(
            parse_result=parse_result, config=config,
        )
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# TYP010: Disallow legacy typing syntax
# =============================================================================


class TestTYP010LegacyTypingSyntax:
    """
    TYP010: Disallow legacy typing syntax.

    This rule enforces modern typing syntax (PEP 585 / PEP 604) for Python 3.11+.

    Violations:
    - Optional[T] should be T | None
    - Union[A, B] should be A | B
    - List[T] should be list[T]
    - Dict[K, V] should be dict[K, V]
    - Tuple[T, ...] should be tuple[T, ...]
    - Set[T] should be set[T]
    - FrozenSet[T] should be frozenset[T]
    - Type[T] should be type[T]
    """

    def test_optional_legacy_syntax(self) -> None:
        """
        Scenario: Using Optional[T] instead of T | None.

        The linter should flag Optional usage as legacy syntax.
        """
        code_sample: str = '''\
from typing import Optional

def find_user(user_id: int) -> Optional[str]:
    return None
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'str | None' instead of 'Optional[str]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_union_legacy_syntax(self) -> None:
        """
        Scenario: Using Union[A, B] instead of A | B.

        The linter should flag Union usage as legacy syntax.
        """
        code_sample: str = '''\
from typing import Union

def parse(value: Union[str, int]) -> str:
    return str(value)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'str | int' instead of 'Union[str, int]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_list_legacy_syntax(self) -> None:
        """
        Scenario: Using List[T] instead of list[T].

        Generic collection types should use built-in syntax.
        """
        code_sample: str = '''\
from typing import List, Dict

def get_names() -> List[str]:
    return []

def get_mapping() -> Dict[str, int]:
    return {}
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'list[str]' instead of 'List[str]'",
            ),
            ExpectedDiagnostic(
                line=6,
                code="TYP010",
                message="Use 'dict[str, int]' instead of 'Dict[str, int]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_tuple_legacy_syntax(self) -> None:
        """
        Scenario: Using Tuple[T, ...] instead of tuple[T, ...].
        """
        code_sample: str = '''\
from typing import Tuple

def get_coords() -> Tuple[int, int]:
    return (0, 0)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'tuple[int, int]' instead of 'Tuple[int, int]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_set_frozenset_legacy_syntax(self) -> None:
        """
        Scenario: Using Set[T] and FrozenSet[T] instead of modern syntax.
        """
        code_sample: str = '''\
from typing import Set, FrozenSet

def get_tags() -> Set[str]:
    return set()

def get_constants() -> FrozenSet[int]:
    return frozenset()
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'set[str]' instead of 'Set[str]'",
            ),
            ExpectedDiagnostic(
                line=6,
                code="TYP010",
                message="Use 'frozenset[int]' instead of 'FrozenSet[int]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_nested_legacy_syntax(self) -> None:
        """
        Scenario: Nested legacy typing constructs.

        All nested legacy types should be flagged.
        """
        code_sample: str = '''\
from typing import Dict, List, Optional

def process() -> Optional[Dict[str, List[int]]]:
    return None
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="TYP010",
                message="Use 'dict[str, list[int]] | None' instead of "
                "'Optional[Dict[str, List[int]]]'",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_modern_syntax_ok(self) -> None:
        """
        Scenario: Using modern typing syntax.

        No diagnostics should be generated for proper modern syntax.
        """
        code_sample: str = '''\
def get_data() -> dict[str, list[int]] | None:
    return None
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="TYP010")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# KW001: Require keyword-only parameters
# =============================================================================


class TestKW001KeywordOnlyParameters:
    """
    KW001: Require keyword-only parameters.

    This rule enforces the use of * to make parameters keyword-only for
    non-trivial functions (public API functions by default).

    Exemptions (configurable):
    - dunder methods (__init__, __call__, etc.)
    - Single-parameter functions
    - Functions with 2 parameters where first is self/cls
    - @override decorated methods
    - Protocol implementations
    - Private functions (underscore prefix)
    """

    def test_public_function_needs_keyword_only(self) -> None:
        """
        Scenario: Public function with multiple positional parameters.

        Public functions with multiple parameters should use keyword-only
        syntax to improve API clarity and prevent positional argument errors.
        """
        code_sample: str = '''\
def create_user(name: str, email: str, age: int) -> dict[str, str | int]:
    return {"name": name, "email": email, "age": age}
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="KW001",
                message="Function 'create_user' should use keyword-only parameters "
                "(add * separator)",
            ),
        ]

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_keyword_only_syntax_ok(self) -> None:
        """
        Scenario: Function correctly using keyword-only parameters.

        No diagnostics when * separator is used.
        """
        code_sample: str = '''\
def create_user(*, name: str, email: str, age: int) -> dict[str, str | int]:
    return {"name": name, "email": email, "age": age}
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_single_parameter_exempted(self) -> None:
        """
        Scenario: Single-parameter function.

        Functions with only one parameter don't need keyword-only syntax.
        """
        code_sample: str = '''\
def get_user(user_id: int) -> dict[str, str]:
    return {"id": str(user_id)}
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_private_function_exempted(self) -> None:
        """
        Scenario: Private function (underscore prefix).

        Private/internal functions are exempted by default.
        """
        code_sample: str = '''\
def _internal_helper(a: int, b: int, c: int) -> int:
    return a + b + c
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_dunder_method_exempted(self) -> None:
        """
        Scenario: Dunder methods.

        Dunder methods like __init__ are exempted as they follow
        Python conventions for positional parameters.
        """
        code_sample: str = '''\
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_method_with_self_and_one_param_exempted(self) -> None:
        """
        Scenario: Method with self and one additional parameter.

        Methods with only one non-self parameter don't need keyword-only syntax.
        """
        code_sample: str = '''\
class Calculator:
    def double(self, value: int) -> int:
        return value * 2
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)

    def test_method_with_multiple_params_needs_keyword_only(self) -> None:
        """
        Scenario: Public method with multiple parameters.

        Methods with multiple non-self parameters should use keyword-only syntax.
        """
        code_sample: str = '''\
class Calculator:
    def compute(self, a: int, b: int, operation: str) -> int:
        return a + b
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="KW001",
                message="Method 'compute' should use keyword-only parameters "
                "(add * separator)",
            ),
        ]

        actual: list[Diagnostic] = _check_code(code_sample, rule_code="KW001")
        _assert_diagnostics_match(actual, expected_diagnostics)


# =============================================================================
# RET001: Disallow heterogeneous tuple returns
# =============================================================================


class TestRET001NoTuplePacking:
    """
    RET001: Disallow heterogeneous tuple returns.

    This rule discourages returning multiple values as tuples (tuple packing)
    because it reduces code clarity and type safety.

    Preferred alternatives:
    - @dataclass(frozen=True, slots=True)
    - NamedTuple

    Exemptions:
    - Homogeneous variadic tuples (e.g., tuple[str, ...])
    - Private functions (configurable)
    - Generator yield expressions
    """

    def test_basic_tuple_return(self) -> None:
        """
        Scenario: Function returning a heterogeneous tuple.

        Returning multiple values via tuple packing should be flagged.
        """
        code_sample: str = '''\
def get_user_info(user_id: int) -> tuple[str, int, bool]:
    return "Alice", 30, True
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="RET001",
                message="Avoid tuple packing for return values; "
                "use a dataclass or NamedTuple",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_implicit_tuple_return(self) -> None:
        """
        Scenario: Implicit tuple return (no parentheses).

        Even without explicit tuple syntax, multiple return values should be flagged.
        """
        code_sample: str = '''\
def divide(a: int, b: int) -> tuple[int, int]:
    quotient = a // b
    remainder = a % b
    return quotient, remainder
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=4,
                code="RET001",
                message="Avoid tuple packing for return values; "
                "use a dataclass or NamedTuple",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_homogeneous_tuple_ok(self) -> None:
        """
        Scenario: Function returning homogeneous tuple.

        Variadic homogeneous tuples (tuple[T, ...]) are acceptable.
        """
        code_sample: str = '''\
def get_ids() -> tuple[int, ...]:
    return (1, 2, 3, 4, 5)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_single_value_return_ok(self) -> None:
        """
        Scenario: Function returning a single value.

        Single value returns are always acceptable.
        """
        code_sample: str = '''\
def get_name() -> str:
    return "Alice"
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_dataclass_return_ok(self) -> None:
        """
        Scenario: Function returning a dataclass instance.

        Using structured types for multi-value returns is the preferred pattern.
        """
        code_sample: str = '''\
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class UserInfo:
    name: str
    age: int
    active: bool

def get_user_info(user_id: int) -> UserInfo:
    return UserInfo(name="Alice", age=30, active=True)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_namedtuple_return_ok(self) -> None:
        """
        Scenario: Function returning a NamedTuple instance.

        NamedTuples are acceptable for structured returns.
        """
        code_sample: str = '''\
from typing import NamedTuple

class DivisionResult(NamedTuple):
    quotient: int
    remainder: int

def divide(a: int, b: int) -> DivisionResult:
    return DivisionResult(quotient=a // b, remainder=a % b)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="RET001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# IMP001: Disallow imports inside function bodies
# =============================================================================


class TestIMP001NoLocalImports:
    """
    IMP001: Disallow imports inside function bodies.

    This rule enforces that all imports are at the top level of the module.
    Local imports make code harder to understand and can hide dependencies.

    Exemptions:
    - TYPE_CHECKING blocks
    - Conditional imports for optional dependencies (must be documented)
    """

    def test_basic_local_import(self) -> None:
        """
        Scenario: Import inside function body.

        The linter should flag imports that are not at module level.
        """
        code_sample: str = '''\
def process_json(data: str) -> dict[str, object]:
    import json
    return json.loads(data)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="IMP001",
                message="Import 'json' should be at module level, not inside function",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_from_import_local(self) -> None:
        """
        Scenario: From import inside function body.

        From imports inside functions should also be flagged.
        """
        code_sample: str = '''\
def get_path() -> str:
    from pathlib import Path
    return str(Path.cwd())
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="IMP001",
                message="Import 'pathlib.Path' should be at module level, "
                "not inside function",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_multiple_local_imports(self) -> None:
        """
        Scenario: Multiple imports inside function body.

        Each local import should be reported.
        """
        code_sample: str = '''\
def complex_operation(x: int) -> str:
    import json
    import re
    from datetime import datetime
    return str(datetime.now())
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=2,
                code="IMP001",
                message="Import 'json' should be at module level, not inside function",
            ),
            ExpectedDiagnostic(
                line=3,
                code="IMP001",
                message="Import 're' should be at module level, not inside function",
            ),
            ExpectedDiagnostic(
                line=4,
                code="IMP001",
                message="Import 'datetime.datetime' should be at module level, "
                "not inside function",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_nested_function_local_import(self) -> None:
        """
        Scenario: Import inside nested function.

        Local imports in nested functions should also be flagged.
        """
        code_sample: str = '''\
def outer() -> str:
    def inner() -> str:
        import os
        return os.getcwd()
    return inner()
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="IMP001",
                message="Import 'os' should be at module level, not inside function",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_method_local_import(self) -> None:
        """
        Scenario: Import inside method body.

        Method bodies should also be checked for local imports.
        """
        code_sample: str = '''\
class DataProcessor:
    def process(self, data: str) -> dict[str, object]:
        import json
        return json.loads(data)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=3,
                code="IMP001",
                message="Import 'json' should be at module level, not inside function",
            ),
        ]

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_top_level_import_ok(self) -> None:
        """
        Scenario: Proper top-level imports.

        No diagnostics should be generated for properly placed imports.
        """
        code_sample: str = '''\
import json
from pathlib import Path

def process_json(data: str) -> dict[str, object]:
    return json.loads(data)

def get_path() -> str:
    return str(Path.cwd())
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)

    def test_type_checking_import_ok(self) -> None:
        """
        Scenario: Import inside TYPE_CHECKING block.

        Imports inside TYPE_CHECKING are acceptable for avoiding circular imports.
        """
        code_sample: str = '''\
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from some_module import SomeType

def process(item: "SomeType") -> None:
    pass
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        diagnostics: list[Diagnostic] = _check_code(code_sample, rule_code="IMP001")
        _assert_diagnostics_match(diagnostics, expected_diagnostics)


# =============================================================================
# EXP001: Structured return types must be module-level and importable
# =============================================================================


@pytest.mark.skip(reason="EXP001 rule not yet implemented")
class TestEXP001ExportableReturnTypes:
    """
    EXP001: Structured return types must be module-level and importable.

    This rule ensures that custom return types (dataclasses, NamedTuples)
    used by public functions are defined at module level so they can be
    imported by consumers.
    """

    def test_nested_dataclass_return_type(self) -> None:
        """
        Scenario: Dataclass defined inside function used as return type.

        Return types should be module-level for importability.
        """
        code_sample: str = '''\
from dataclasses import dataclass

def get_result() -> "Result":
    @dataclass
    class Result:
        value: int
        success: bool
    return Result(value=42, success=True)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=4,
                code="EXP001",
                message="Return type 'Result' should be defined at module level "
                "for importability",
            ),
        ]

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - EXP001 rule pending"

    def test_module_level_return_type_ok(self) -> None:
        """
        Scenario: Dataclass defined at module level.

        Module-level type definitions are acceptable.
        """
        code_sample: str = '''\
from dataclasses import dataclass

@dataclass
class Result:
    value: int
    success: bool

def get_result() -> Result:
    return Result(value=42, success=True)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - EXP001 rule pending"


# =============================================================================
# EXP002: Enforce __all__ or explicit re-export policy
# =============================================================================


@pytest.mark.skip(reason="EXP002 rule not yet implemented")
class TestEXP002ExplicitExports:
    """
    EXP002: Enforce __all__ or explicit re-export policy.

    This rule enforces that modules explicitly define their public API
    through __all__ or other explicit export mechanisms.

    This is an optional/configurable rule that helps maintain clear
    module boundaries.
    """

    def test_missing_all_definition(self) -> None:
        """
        Scenario: Module without __all__ definition.

        Public modules should define __all__ to clarify their API.
        """
        code_sample: str = '''\
def public_function() -> str:
    return "hello"

def another_public_function() -> int:
    return 42
'''
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="EXP002",
                message="Module should define '__all__' to explicitly declare public API",
            ),
        ]

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - EXP002 rule pending"

    def test_all_defined_ok(self) -> None:
        """
        Scenario: Module with __all__ definition.

        No diagnostics when __all__ is defined.
        """
        code_sample: str = '''\
__all__ = ["public_function", "another_public_function"]

def public_function() -> str:
    return "hello"

def another_public_function() -> int:
    return 42

def _private_helper() -> None:
    pass
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - EXP002 rule pending"


# =============================================================================
# Ignore/Skip Pragma Tests
# =============================================================================


@pytest.mark.skip(reason="Ignore pragma system not yet implemented")
class TestIgnorePragmas:
    """
    Tests for the ignore/skip pragma system.

    PyGuard supports three levels of ignore pragmas:
    - Line: # pyguard: ignore[CODE1,CODE2] because: ...
    - Block/function: # pyguard: ignore[CODE] because: ... (preceding definition)
    - File: # pyguard: ignore-file[CODE] because: ... (at top of file)

    Governance options:
    - require_ignore_reason = true
    - disallow_ignores = ["TYP002"]
    - max_ignores_per_file = N
    """

    def test_line_level_ignore(self) -> None:
        """
        Scenario: Ignoring a specific rule on a single line.

        The diagnostic should be suppressed for the ignored line only.
        """
        code_sample: str = '''\
def add(x, y):  # pyguard: ignore[TYP001] because: legacy function
    return x + y
'''
        # TYP001 should be suppressed for line 1
        expected_diagnostics: list[ExpectedDiagnostic] = []

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - ignore pragma system pending"

    def test_block_level_ignore(self) -> None:
        """
        Scenario: Ignoring a rule for an entire function.

        The pragma before the function suppresses diagnostics for the whole block.
        """
        code_sample: str = '''\
# pyguard: ignore[TYP001,TYP002] because: external API callback
def legacy_callback(event, data):
    return process(event, data)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - ignore pragma system pending"

    def test_file_level_ignore(self) -> None:
        """
        Scenario: Ignoring a rule for the entire file.

        The file-level pragma at the top suppresses diagnostics throughout.
        """
        code_sample: str = '''\
# pyguard: ignore-file[IMP001] because: plugin module with dynamic imports

def load_plugin(name: str) -> object:
    import importlib
    return importlib.import_module(name)
'''
        expected_diagnostics: list[ExpectedDiagnostic] = []

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - ignore pragma system pending"

    def test_require_ignore_reason(self) -> None:
        """
        Scenario: Ignore pragma without reason when reasons are required.

        When require_ignore_reason = true, ignores without reasons should be flagged.
        """
        code_sample: str = '''\
def add(x, y):  # pyguard: ignore[TYP001]
    return x + y
'''
        # Configuration: require_ignore_reason = true
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="IGN001",
                message="Ignore pragma requires a reason (use 'because: ...')",
            ),
        ]

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - ignore pragma system pending"

    def test_disallowed_ignore_code(self) -> None:
        """
        Scenario: Attempting to ignore a disallowed rule code.

        When a code is in disallow_ignores, the pragma should be rejected.
        """
        code_sample: str = '''\
def get_value():  # pyguard: ignore[TYP002] because: not needed
    return 42
'''
        # Configuration: disallow_ignores = ["TYP002"]
        expected_diagnostics: list[ExpectedDiagnostic] = [
            ExpectedDiagnostic(
                line=1,
                code="IGN002",
                message="Rule 'TYP002' cannot be ignored (disallowed by configuration)",
            ),
            ExpectedDiagnostic(
                line=1,
                code="TYP002",
                message="Missing return type annotation for function 'get_value'",
            ),
        ]

        _unused = (code_sample, expected_diagnostics)
        assert False, "Test not implemented - ignore pragma system pending"


# =============================================================================
# Test Utilities (to be implemented with the linter)
# =============================================================================


def assert_diagnostics_match(
    *,
    actual: list[ExpectedDiagnostic],
    expected: list[ExpectedDiagnostic],
) -> None:
    """
    Assert that actual diagnostics match expected ones.

    This will be used when the linter is implemented.
    """
    assert len(actual) == len(expected), (
        f"Expected {len(expected)} diagnostics, got {len(actual)}"
    )
    for act, exp in zip(actual, expected, strict=True):
        assert act.line == exp.line, f"Line mismatch: {act.line} != {exp.line}"
        assert act.code == exp.code, f"Code mismatch: {act.code} != {exp.code}"
        assert exp.message in act.message, (
            f"Message mismatch: expected '{exp.message}' in '{act.message}'"
        )
