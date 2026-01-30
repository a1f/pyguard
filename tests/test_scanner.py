"""Tests for PyGuard file scanner."""
from __future__ import annotations

from pathlib import Path

import pytest

from pyguard.scanner import scan_files
from pyguard.types import PyGuardConfig


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a sample project structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "pkg").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".hidden").mkdir()

    (tmp_path / "main.py").write_text("# main")
    (tmp_path / "src" / "app.py").write_text("# app")
    (tmp_path / "src" / "pkg" / "module.py").write_text("# module")
    (tmp_path / "src" / "pkg" / "__init__.py").write_text("")
    (tmp_path / "tests" / "test_app.py").write_text("# test")
    (tmp_path / "__pycache__" / "cached.cpython-311.pyc").write_bytes(b"")
    (tmp_path / "__pycache__" / "module.py").write_text("# cached py")
    (tmp_path / ".hidden" / "secret.py").write_text("# hidden")

    (tmp_path / "README.md").write_text("# README")
    (tmp_path / "src" / "data.json").write_text("{}")

    return tmp_path


def test_scan_single_python_file(tmp_path: Path) -> None:
    py_file = tmp_path / "test.py"
    py_file.write_text("# test")

    result = scan_files(paths=(py_file,), config=PyGuardConfig())

    assert result == [py_file.resolve()]


def test_scan_ignores_non_python_files(tmp_path: Path) -> None:
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not python")

    result = scan_files(paths=(txt_file,), config=PyGuardConfig())

    assert result == []


def test_scan_directory_finds_all_python_files(sample_project: Path) -> None:
    config = PyGuardConfig(
        include=("**/*.py",),
        exclude=("**/__pycache__/**", "**/.*/**"),
    )

    result = scan_files(paths=(sample_project,), config=config)

    file_names = {p.name for p in result}
    assert file_names == {"main.py", "app.py", "module.py", "__init__.py", "test_app.py"}


def test_exclude_pycache(sample_project: Path) -> None:
    config = PyGuardConfig(include=("**/*.py",), exclude=("**/__pycache__/**",))

    result = scan_files(paths=(sample_project,), config=config)

    for path in result:
        assert "__pycache__" not in path.parts


def test_exclude_dotfiles(sample_project: Path) -> None:
    config = PyGuardConfig(include=("**/*.py",), exclude=("**/.*/**",))

    result = scan_files(paths=(sample_project,), config=config)

    for path in result:
        assert not any(part.startswith(".") for part in path.parts)


def test_exclude_test_files(sample_project: Path) -> None:
    config = PyGuardConfig(include=("**/*.py",), exclude=("**/test_*.py",))

    result = scan_files(paths=(sample_project,), config=config)

    assert not any(p.name.startswith("test_") for p in result)


def test_include_pattern_limits_files(sample_project: Path) -> None:
    config = PyGuardConfig(include=("src/**/*.py",), exclude=())

    result = scan_files(paths=(sample_project,), config=config)

    file_names = {p.name for p in result}
    assert "app.py" in file_names
    assert "module.py" in file_names
    assert "main.py" not in file_names
    assert "test_app.py" not in file_names


def test_multiple_paths(tmp_path: Path) -> None:
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "a.py").write_text("# a")
    (dir2 / "b.py").write_text("# b")

    result = scan_files(paths=(dir1, dir2), config=PyGuardConfig())

    assert len(result) == 2
    assert {p.name for p in result} == {"a.py", "b.py"}


def test_results_are_sorted(tmp_path: Path) -> None:
    for name in ["z.py", "a.py", "m.py"]:
        (tmp_path / name).write_text("")

    result = scan_files(paths=(tmp_path,), config=PyGuardConfig())

    names = [p.name for p in result]
    assert names == sorted(names)


def test_empty_directory_returns_empty_list(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = scan_files(paths=(empty_dir,), config=PyGuardConfig())

    assert result == []


def test_default_excludes_work(sample_project: Path) -> None:
    result = scan_files(paths=(sample_project,), config=PyGuardConfig())

    for path in result:
        path_str = str(path)
        assert "__pycache__" not in path_str
        assert ".hidden" not in path_str
