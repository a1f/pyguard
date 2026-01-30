"""Tests for PyGuard file scanner."""
from __future__ import annotations

from pathlib import Path

import pytest

from pyguard.scanner import scan_files
from pyguard.types import PyGuardConfig


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a sample project structure for testing."""
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


class TestScanFiles:
    """Tests for scan_files function."""

    def test_scan_single_file(self, tmp_path: Path) -> None:
        py_file: Path = tmp_path / "test.py"
        py_file.write_text("# test")

        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(py_file,), config=config)

        assert len(result) == 1
        assert result[0] == py_file.resolve()

    def test_scan_non_python_file(self, tmp_path: Path) -> None:
        txt_file: Path = tmp_path / "test.txt"
        txt_file.write_text("not python")

        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(txt_file,), config=config)

        assert len(result) == 0

    def test_scan_directory(self, sample_project: Path) -> None:
        config: PyGuardConfig = PyGuardConfig(
            include=("**/*.py",),
            exclude=("**/__pycache__/**", "**/.*/**"),
        )
        result: list[Path] = scan_files(paths=(sample_project,), config=config)

        file_names: set[str] = {p.name for p in result}
        assert "main.py" in file_names
        assert "app.py" in file_names
        assert "module.py" in file_names
        assert "__init__.py" in file_names
        assert "test_app.py" in file_names

    def test_exclude_pycache(self, sample_project: Path) -> None:
        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(sample_project,), config=config)

        for path in result:
            assert "__pycache__" not in str(path)

    def test_exclude_dotfiles(self, sample_project: Path) -> None:
        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(sample_project,), config=config)

        for path in result:
            assert ".hidden" not in str(path)

    def test_include_pattern(self, sample_project: Path) -> None:
        config: PyGuardConfig = PyGuardConfig(
            include=("src/**/*.py",),
            exclude=(),
        )
        result: list[Path] = scan_files(paths=(sample_project,), config=config)

        file_names: set[str] = {p.name for p in result}
        assert "app.py" in file_names
        assert "module.py" in file_names
        assert "main.py" not in file_names
        assert "test_app.py" not in file_names

    def test_exclude_pattern(self, sample_project: Path) -> None:
        config: PyGuardConfig = PyGuardConfig(
            include=("**/*.py",),
            exclude=("**/test_*.py",),
        )
        result: list[Path] = scan_files(paths=(sample_project,), config=config)

        file_names: set[str] = {p.name for p in result}
        assert "test_app.py" not in file_names
        assert "app.py" in file_names

    def test_multiple_paths(self, tmp_path: Path) -> None:
        dir1: Path = tmp_path / "dir1"
        dir2: Path = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "a.py").write_text("# a")
        (dir2 / "b.py").write_text("# b")

        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(dir1, dir2), config=config)

        assert len(result) == 2
        file_names: set[str] = {p.name for p in result}
        assert "a.py" in file_names
        assert "b.py" in file_names

    def test_results_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "z.py").write_text("")
        (tmp_path / "a.py").write_text("")
        (tmp_path / "m.py").write_text("")

        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(tmp_path,), config=config)

        names: list[str] = [p.name for p in result]
        assert names == sorted(names)

    def test_empty_directory(self, tmp_path: Path) -> None:
        empty_dir: Path = tmp_path / "empty"
        empty_dir.mkdir()

        config: PyGuardConfig = PyGuardConfig()
        result: list[Path] = scan_files(paths=(empty_dir,), config=config)

        assert result == []
