"""Tests for the ignore pragma system (parsing, filtering, governance)."""
from __future__ import annotations

import ast
from pathlib import Path

from pyguard.constants import IGN001_CODE, IGN002_CODE, IGN003_CODE, Severity
from pyguard.diagnostics import Diagnostic, SourceLocation
from pyguard.ignores import IgnoreDirective, apply_ignores, parse_ignore_directives
from pyguard.parser import ParseResult
from pyguard.types import IgnoreGovernance

_TEST_FILE: Path = Path("test.py")

_QUIET_GOVERNANCE: IgnoreGovernance = IgnoreGovernance(require_reason=False)


def _make_parse_result(code: str) -> ParseResult:
    file: Path = _TEST_FILE
    source_lines: tuple[str, ...] = tuple(code.splitlines())
    tree: ast.Module = ast.parse(code, filename=str(file))
    return ParseResult(
        file=file,
        tree=tree,
        source=code,
        source_lines=source_lines,
        syntax_error=None,
    )


def _make_diagnostic(
    *,
    file: Path = _TEST_FILE,
    line: int,
    code: str,
    message: str = "test",
) -> Diagnostic:
    return Diagnostic(
        file=file,
        location=SourceLocation(line=line, column=1),
        code=code,
        message=message,
        severity=Severity.ERROR,
        source_line=None,
    )


# ---------------------------------------------------------------------------
# TestParseIgnoreDirectives
# ---------------------------------------------------------------------------


class TestParseIgnoreDirectives:
    def test_no_directives(self) -> None:
        source_lines: tuple[str, ...] = (
            "def add(x, y):",
            "    return x + y",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert result == []

    def test_line_level_inline(self) -> None:
        source_lines: tuple[str, ...] = (
            "def add(x, y):  # pyguard: ignore[TYP001] because: legacy",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        directive: IgnoreDirective = result[0]
        assert directive.line == 1
        assert directive.codes == frozenset({"TYP001"})
        assert directive.reason == "legacy"
        assert directive.is_inline is True
        assert directive.is_file_level is False

    def test_block_level_standalone(self) -> None:
        source_lines: tuple[str, ...] = (
            "# pyguard: ignore[TYP001] because: legacy",
            "def add(x, y):",
            "    return x + y",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        directive: IgnoreDirective = result[0]
        assert directive.line == 1
        assert directive.is_inline is False
        assert directive.is_file_level is False

    def test_file_level(self) -> None:
        source_lines: tuple[str, ...] = (
            "# pyguard: ignore-file[IMP001] because: plugin",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        directive: IgnoreDirective = result[0]
        assert directive.line == 1
        assert directive.codes == frozenset({"IMP001"})
        assert directive.reason == "plugin"
        assert directive.is_file_level is True
        assert directive.is_inline is False

    def test_multiple_codes(self) -> None:
        source_lines: tuple[str, ...] = (
            "# pyguard: ignore[TYP001,TYP002] because: legacy",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        assert result[0].codes == frozenset({"TYP001", "TYP002"})

    def test_no_reason(self) -> None:
        source_lines: tuple[str, ...] = (
            "# pyguard: ignore[TYP001]",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        assert result[0].reason is None

    def test_indented_standalone(self) -> None:
        source_lines: tuple[str, ...] = (
            "def outer():",
            "    # pyguard: ignore[TYP001] because: x",
            "    def inner(a):",
            "        pass",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 1
        directive: IgnoreDirective = result[0]
        assert directive.line == 2
        assert directive.is_inline is False
        assert directive.is_file_level is False

    def test_multiple_directives(self) -> None:
        source_lines: tuple[str, ...] = (
            "# pyguard: ignore-file[IMP001] because: plugin",
            "# pyguard: ignore[TYP001] because: block-level",
            "def add(x, y):  # pyguard: ignore[TYP002] because: inline",
            "    return x + y",
        )
        result: list[IgnoreDirective] = parse_ignore_directives(
            source_lines=source_lines,
        )
        assert len(result) == 3
        assert result[0].is_file_level is True
        assert result[0].codes == frozenset({"IMP001"})
        assert result[1].is_inline is False
        assert result[1].is_file_level is False
        assert result[1].codes == frozenset({"TYP001"})
        assert result[2].is_inline is True
        assert result[2].codes == frozenset({"TYP002"})


# ---------------------------------------------------------------------------
# TestApplyIgnoresLinelevel
# ---------------------------------------------------------------------------


class TestApplyIgnoresLinelevel:
    def test_inline_ignore_suppresses_matching_code(self) -> None:
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001] because: legacy\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag: Diagnostic = _make_diagnostic(line=1, code="TYP001")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert result == []

    def test_inline_ignore_does_not_affect_other_lines(self) -> None:
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001] because: legacy\n"
            "    return x + y\n"
            "def sub(a, b):\n"
            "    return a - b\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag_line1: Diagnostic = _make_diagnostic(line=1, code="TYP001")
        diag_line3: Diagnostic = _make_diagnostic(line=3, code="TYP001")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag_line1, diag_line3],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert len(result) == 1
        assert result[0].location.line == 3

    def test_inline_ignore_different_code_not_suppressed(self) -> None:
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001] because: legacy\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag: Diagnostic = _make_diagnostic(line=1, code="TYP002")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert len(result) == 1
        assert result[0].code == "TYP002"


# ---------------------------------------------------------------------------
# TestApplyIgnoresBlockLevel
# ---------------------------------------------------------------------------


class TestApplyIgnoresBlockLevel:
    def test_block_ignore_suppresses_entire_function(self) -> None:
        code: str = (
            "# pyguard: ignore[TYP001] because: generated code\n"
            "def add(x, y):\n"
            "    z = x + y\n"
            "    return z\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag_line2: Diagnostic = _make_diagnostic(line=2, code="TYP001")
        diag_line3: Diagnostic = _make_diagnostic(line=3, code="TYP001")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag_line2, diag_line3],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert result == []

    def test_block_ignore_does_not_affect_outside_block(self) -> None:
        code: str = (
            "# pyguard: ignore[TYP001] because: generated code\n"
            "def add(x, y):\n"
            "    return x + y\n"
            "def sub(a, b):\n"
            "    return a - b\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag_inside: Diagnostic = _make_diagnostic(line=2, code="TYP001")
        diag_outside: Diagnostic = _make_diagnostic(line=4, code="TYP001")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag_inside, diag_outside],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert len(result) == 1
        assert result[0].location.line == 4


# ---------------------------------------------------------------------------
# TestApplyIgnoresFileLevel
# ---------------------------------------------------------------------------


class TestApplyIgnoresFileLevel:
    def test_file_ignore_suppresses_all_matching(self) -> None:
        code: str = (
            "# pyguard: ignore-file[TYP001] because: legacy module\n"
            "def add(x, y):\n"
            "    return x + y\n"
            "def sub(a, b):\n"
            "    return a - b\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag1: Diagnostic = _make_diagnostic(line=2, code="TYP001")
        diag2: Diagnostic = _make_diagnostic(line=4, code="TYP001")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag1, diag2],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert result == []

    def test_file_ignore_does_not_affect_other_codes(self) -> None:
        code: str = (
            "# pyguard: ignore-file[TYP001] because: legacy module\n"
            "def add(x, y):\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag_typ001: Diagnostic = _make_diagnostic(line=2, code="TYP001")
        diag_typ002: Diagnostic = _make_diagnostic(line=2, code="TYP002")
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag_typ001, diag_typ002],
            parse_result=pr,
            governance=_QUIET_GOVERNANCE,
        )
        assert len(result) == 1
        assert result[0].code == "TYP002"


# ---------------------------------------------------------------------------
# TestGovernance
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_require_reason_generates_ign001(self) -> None:
        """When require_reason=True and no reason, IGN001 is emitted but
        the original diagnostic is still suppressed by the ignore."""
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001]\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag: Diagnostic = _make_diagnostic(line=1, code="TYP001")
        governance: IgnoreGovernance = IgnoreGovernance(require_reason=True)
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag],
            parse_result=pr,
            governance=governance,
        )
        # Original TYP001 is suppressed; IGN001 is emitted for missing reason
        ign_codes: list[str] = [d.code for d in result]
        assert IGN001_CODE in ign_codes
        assert "TYP001" not in ign_codes

    def test_require_reason_false_no_ign001(self) -> None:
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001]\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag: Diagnostic = _make_diagnostic(line=1, code="TYP001")
        governance: IgnoreGovernance = IgnoreGovernance(require_reason=False)
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag],
            parse_result=pr,
            governance=governance,
        )
        ign_codes: list[str] = [d.code for d in result]
        assert IGN001_CODE not in ign_codes
        assert "TYP001" not in ign_codes

    def test_disallow_generates_ign002_and_keeps_diagnostic(self) -> None:
        """When a code is in the disallow set, IGN002 is emitted and the
        original diagnostic is NOT suppressed."""
        code: str = (
            "def add(x, y):  # pyguard: ignore[TYP001] because: legacy\n"
            "    return x + y\n"
        )
        pr: ParseResult = _make_parse_result(code)
        diag: Diagnostic = _make_diagnostic(line=1, code="TYP001")
        governance: IgnoreGovernance = IgnoreGovernance(
            require_reason=False,
            disallow=frozenset({"TYP001"}),
        )
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[diag],
            parse_result=pr,
            governance=governance,
        )
        result_codes: list[str] = [d.code for d in result]
        assert IGN002_CODE in result_codes
        assert "TYP001" in result_codes

    def test_max_per_file_generates_ign003(self) -> None:
        code: str = (
            "x = 1  # pyguard: ignore[TYP001] because: a\n"
            "y = 2  # pyguard: ignore[TYP001] because: b\n"
            "z = 3  # pyguard: ignore[TYP001] because: c\n"
        )
        pr: ParseResult = _make_parse_result(code)
        governance: IgnoreGovernance = IgnoreGovernance(
            require_reason=False,
            max_per_file=2,
        )
        result: list[Diagnostic] = apply_ignores(
            diagnostics=[],
            parse_result=pr,
            governance=governance,
        )
        result_codes: list[str] = [d.code for d in result]
        assert IGN003_CODE in result_codes
        ign003_diags: list[Diagnostic] = [
            d for d in result if d.code == IGN003_CODE
        ]
        assert len(ign003_diags) == 1
        assert "3 ignore directives" in ign003_diags[0].message
        assert "maximum allowed is 2" in ign003_diags[0].message
