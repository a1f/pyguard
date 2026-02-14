"""Rule documentation catalog for pyguard explain command."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class RuleInfo:
    code: str
    name: str
    category: str
    description: str
    bad_example: str
    good_example: str
    has_autofix: bool
    fix_description: str
    config_options: str


RULE_CATALOG: Final[dict[str, RuleInfo]] = {
    "TYP001": RuleInfo(
        code="TYP001",
        name="Missing Parameter Annotations",
        category="typing",
        description=(
            "All function parameters must have type annotations.\n"
            "This makes function signatures self-documenting and enables\n"
            "static type checking with mypy or pyright."
        ),
        bad_example="def greet(name): ...",
        good_example="def greet(name: str) -> None: ...",
        has_autofix=False,
        fix_description="",
        config_options=(
            "[tool.pyguard.rules.TYP001]\n"
            "exempt_dunder = true    # Skip __init__, __str__, etc.\n"
            "exempt_self_cls = true  # Skip self/cls parameters"
        ),
    ),
    "TYP002": RuleInfo(
        code="TYP002",
        name="Missing Return Annotation",
        category="typing",
        description=(
            "All functions must have a return type annotation.\n"
            "Explicit return types document the function contract and\n"
            "catch accidental return value changes."
        ),
        bad_example="def greet(name: str): ...",
        good_example="def greet(name: str) -> None: ...",
        has_autofix=True,
        fix_description="Adds -> None to functions that lack a return annotation.",
        config_options="",
    ),
    "TYP003": RuleInfo(
        code="TYP003",
        name="Missing Variable Annotation",
        category="typing",
        description=(
            "Variables should have type annotations, especially at module\n"
            "and class scope. This aids readability and enables type checkers\n"
            "to verify assignments."
        ),
        bad_example="MAX_RETRIES = 3",
        good_example="MAX_RETRIES: int = 3",
        has_autofix=True,
        fix_description="Infers type from the assigned value and adds annotation.",
        config_options=(
            "[tool.pyguard.rules.TYP003]\n"
            "scope = [\"module\"]  # \"module\", \"class\", \"local\""
        ),
    ),
    "TYP010": RuleInfo(
        code="TYP010",
        name="Legacy Typing Syntax",
        category="typing",
        description=(
            "Use modern typing syntax (PEP 585/604) instead of legacy\n"
            "typing module generics. On Python 3.10+, use list[str]\n"
            "instead of List[str] and X | None instead of Optional[X]."
        ),
        bad_example="from typing import List, Optional\ndef f(x: Optional[List[str]]): ...",
        good_example="def f(x: list[str] | None) -> None: ...",
        has_autofix=True,
        fix_description="Transforms legacy typing syntax to modern equivalents using LibCST.",
        config_options="",
    ),
    "KW001": RuleInfo(
        code="KW001",
        name="Missing Keyword-Only Parameters",
        category="api",
        description=(
            "Functions with multiple parameters should use keyword-only\n"
            "arguments (after *) to prevent positional call-site errors\n"
            "and make APIs self-documenting."
        ),
        bad_example="def connect(host: str, port: int, timeout: float): ...",
        good_example="def connect(*, host: str, port: int, timeout: float): ...",
        has_autofix=True,
        fix_description="Inserts * separator before parameters that should be keyword-only.",
        config_options=(
            "[tool.pyguard.rules.KW001]\n"
            "min_params = 2          # Minimum params to trigger\n"
            "exempt_dunder = true    # Skip __init__, etc.\n"
            "exempt_private = true   # Skip _private methods\n"
            "exempt_overrides = true # Skip methods with @override"
        ),
    ),
    "RET001": RuleInfo(
        code="RET001",
        name="Heterogeneous Tuple Returns",
        category="api",
        description=(
            "Functions should not return heterogeneous tuples like\n"
            "return name, age, active. Use a dataclass or NamedTuple\n"
            "instead for clarity and type safety."
        ),
        bad_example="def get_user() -> tuple[str, int]:\n    return name, age",
        good_example="@dataclass\nclass User:\n    name: str\n    age: int",
        has_autofix=False,
        fix_description="",
        config_options="",
    ),
    "IMP001": RuleInfo(
        code="IMP001",
        name="In-Function Imports",
        category="imports",
        description=(
            "All imports should be at module level, not inside functions.\n"
            "Module-level imports make dependencies visible, improve\n"
            "startup predictability, and enable static analysis."
        ),
        bad_example="def process():\n    import json\n    return json.dumps({})",
        good_example="import json\n\ndef process():\n    return json.dumps({})",
        has_autofix=True,
        fix_description="Moves in-function imports to the top of the module.",
        config_options="",
    ),
    "EXP001": RuleInfo(
        code="EXP001",
        name="Module-Level Return Types",
        category="exports",
        description=(
            "Structured return types (dataclasses, NamedTuples, TypedDicts)\n"
            "used in public function signatures should be defined at module\n"
            "level so they are importable by callers."
        ),
        bad_example="def get_user():\n    class User: ...\n    return User()",
        good_example="class User: ...\n\ndef get_user() -> User: ...",
        has_autofix=False,
        fix_description="",
        config_options="",
    ),
    "EXP002": RuleInfo(
        code="EXP002",
        name="Missing __all__ Declaration",
        category="exports",
        description=(
            "Modules with public symbols should declare __all__ to make\n"
            "the public API explicit. This helps IDE autocompletion,\n"
            "documentation generators, and wildcard imports."
        ),
        bad_example="# module.py\ndef public_func(): ...\ndef _private(): ...",
        good_example='__all__ = ["public_func"]\n\ndef public_func(): ...',
        has_autofix=False,
        fix_description="",
        config_options="",
    ),
}


def format_rule_detail(*, info: RuleInfo, default_severity: str) -> str:
    """Format a single rule's full documentation."""
    lines: list[str] = [
        f"{info.code}: {info.name}",
        f"Category: {info.category} | Default severity: {default_severity}"
        f" | Autofix: {'Yes' if info.has_autofix else 'No'}",
        "",
        f"  {info.description}",
        "",
        f"  Bad:   {info.bad_example.splitlines()[0]}",
        f"  Good:  {info.good_example.splitlines()[0]}",
    ]

    if info.fix_description:
        lines.extend(["", f"  Fix: {info.fix_description}"])

    if info.config_options:
        lines.extend(["", f"  Config: {info.config_options.splitlines()[0]}"])
        for opt_line in info.config_options.splitlines()[1:]:
            lines.append(f"          {opt_line}")

    lines.extend([
        "",
        f"  Suppress: # pyguard: ignore[{info.code}] because: <reason>",
    ])

    return "\n".join(lines)


def format_rule_table(*, catalog: dict[str, RuleInfo], severities: dict[str, str]) -> str:
    """Format all rules as a summary table."""
    lines: list[str] = [
        f"{'CODE':<8} {'SEVERITY':<10} {'NAME':<35} {'FIX':<4}",
        "-" * 60,
    ]
    for code in sorted(catalog):
        info: RuleInfo = catalog[code]
        severity: str = severities.get(code, "off")
        fix_marker: str = "Yes" if info.has_autofix else "-"
        lines.append(f"{code:<8} {severity:<10} {info.name:<35} {fix_marker:<4}")
    return "\n".join(lines)
