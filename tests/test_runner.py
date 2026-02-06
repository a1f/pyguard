"""Tests for PyGuard lint runner."""
from __future__ import annotations

from pathlib import Path

from pyguard.constants import SYNTAX_ERROR_CODE, OutputFormat
from pyguard.runner import LintResult, format_results, lint_paths
from pyguard.types import PyGuardConfig


def _write_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestLintPaths:
    def test_valid_files_no_errors(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "good.py", "x: int = 1\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        assert result.files_checked == 1
        assert result.exit_code == 0
        assert not result.diagnostics.has_errors

    def test_syntax_error_detected(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "bad.py", "def broken(\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        assert result.files_checked == 1
        assert result.exit_code == 1
        assert result.diagnostics.has_errors
        diags = result.diagnostics.sorted
        assert len(diags) == 1
        assert diags[0].code == SYNTAX_ERROR_CODE

    def test_mixed_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "good.py", "x: int = 1\n")
        _write_file(tmp_path / "bad.py", "def broken(\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        assert result.files_checked == 2
        assert result.exit_code == 1
        assert result.diagnostics.error_count == 1

    def test_empty_directory(self, tmp_path: Path) -> None:
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        assert result.files_checked == 0
        assert result.exit_code == 0

    def test_multiple_syntax_errors(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "def f(\n")
        _write_file(tmp_path / "b.py", "class C(\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        assert result.files_checked == 2
        assert result.diagnostics.error_count == 2

    def test_syntax_error_has_source_line(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "bad.py", "def broken(\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        diag = result.diagnostics.sorted[0]
        assert diag.source_line is not None
        assert "broken" in diag.source_line


class TestFormatResults:
    def test_clean_output(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "good.py", "x: int = 1\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        output: str = format_results(result=result, config=PyGuardConfig())
        assert "No issues found." in output
        assert "Checked 1 file." in output

    def test_error_output(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "bad.py", "def broken(\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        output: str = format_results(result=result, config=PyGuardConfig())
        assert "SYN001" in output
        assert "1 error" in output
        assert "Checked 1 file." in output

    def test_plural_files(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "a.py", "x: int = 1\n")
        _write_file(tmp_path / "b.py", "y: int = 2\n")
        result: LintResult = lint_paths(
            paths=(tmp_path,),
            config=PyGuardConfig(),
        )
        output: str = format_results(result=result, config=PyGuardConfig())
        assert "Checked 2 files." in output

    def test_json_format(self, tmp_path: Path) -> None:
        _write_file(tmp_path / "bad.py", "def broken(\n")
        config: PyGuardConfig = PyGuardConfig(output_format=OutputFormat.JSON)
        result: LintResult = lint_paths(paths=(tmp_path,), config=config)
        output: str = format_results(result=result, config=config)
        assert '"code": "SYN001"' in output
