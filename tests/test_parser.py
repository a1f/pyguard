"""Tests for PyGuard AST parser."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyguard.parser import SyntaxErrorInfo, parse_file


def test_parse_valid_file(tmp_path: Path) -> None:
    py_file = tmp_path / "valid.py"
    py_file.write_text("def foo() -> int:\n    return 42\n")

    result = parse_file(file=py_file)

    assert result.file == py_file
    assert result.tree is not None
    assert isinstance(result.tree, ast.Module)
    assert result.syntax_error is None
    assert result.source == "def foo() -> int:\n    return 42\n"
    assert result.source_lines == ("def foo() -> int:", "    return 42")


def test_parse_empty_file(tmp_path: Path) -> None:
    py_file = tmp_path / "empty.py"
    py_file.write_text("")

    result = parse_file(file=py_file)

    assert result.tree is not None
    assert result.syntax_error is None
    assert result.source == ""
    assert result.source_lines == ()


@pytest.mark.parametrize(
    ("content", "expected_line"),
    [
        pytest.param("def broken(\n", 2, id="unclosed_paren"),
        pytest.param("x = 1\ny = \nz = 3", 3, id="incomplete_assignment"),
        pytest.param("class Foo\n", 1, id="missing_colon"),
    ],
)
def test_syntax_error_detected(tmp_path: Path, content: str, expected_line: int) -> None:
    py_file = tmp_path / "bad.py"
    py_file.write_text(content)

    result = parse_file(file=py_file)

    assert result.tree is None
    assert result.syntax_error is not None
    assert result.syntax_error.line in (expected_line, expected_line - 1)
    assert result.syntax_error.column >= 1
    assert result.syntax_error.message != ""


def test_syntax_error_includes_source_line(tmp_path: Path) -> None:
    py_file = tmp_path / "bad.py"
    py_file.write_text("good = 1\nbad syntax here\ngood = 3")

    result = parse_file(file=py_file)

    assert result.syntax_error is not None
    assert result.syntax_error.source_line == "bad syntax here"


def test_file_not_found(tmp_path: Path) -> None:
    py_file = tmp_path / "nonexistent.py"

    result = parse_file(file=py_file)

    assert result.tree is None
    assert result.syntax_error is not None
    assert "Cannot read file" in result.syntax_error.message
    assert result.source == ""


def test_unicode_content(tmp_path: Path) -> None:
    py_file = tmp_path / "unicode.py"
    py_file.write_text("message = 'Café ☕'\n", encoding="utf-8")

    result = parse_file(file=py_file)

    assert result.tree is not None
    assert result.syntax_error is None
    assert "Café" in result.source


def test_encoding_error(tmp_path: Path) -> None:
    py_file = tmp_path / "bad_encoding.py"
    py_file.write_bytes(b"\xff\xfe invalid utf-8 \x80\x81")

    result = parse_file(file=py_file)

    assert result.tree is None
    assert result.syntax_error is not None
    assert "Encoding error" in result.syntax_error.message


def test_source_lines_preserved(tmp_path: Path) -> None:
    py_file = tmp_path / "lines.py"
    py_file.write_text("line1\nline2\nline3")

    result = parse_file(file=py_file)

    assert result.source_lines == ("line1", "line2", "line3")


def test_complex_valid_code(tmp_path: Path) -> None:
    py_file = tmp_path / "complex.py"
    py_file.write_text("""from __future__ import annotations

class MyClass:
    def __init__(self, value: int) -> None:
        self.value: int = value
""")

    result = parse_file(file=py_file)

    assert result.tree is not None
    assert result.syntax_error is None
    class_defs = [n for n in ast.walk(result.tree) if isinstance(n, ast.ClassDef)]
    assert len(class_defs) == 1
    assert class_defs[0].name == "MyClass"


def test_dataclasses_are_frozen() -> None:
    info = SyntaxErrorInfo(line=1, column=1, message="test", source_line=None)
    with pytest.raises(AttributeError):
        info.line = 2  # type: ignore[misc]
