"""Pytest fixtures for PyGuard tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def temp_pyproject(tmp_path: Path) -> Path:
    """Create a temporary pyproject.toml file."""
    config_path: Path = tmp_path / "pyproject.toml"
    config_path.write_text(
        """
[tool.pyguard]
python_version = "3.12"
include = ["src/**/*.py"]
exclude = ["**/test_*.py"]
output_format = "text"
show_source = false
color = "never"

[tool.pyguard.rules]
TYP001 = "warn"
TYP002 = "error"

[tool.pyguard.rules.KW001]
severity = "off"
min_params = 3
exempt_dunder = false

[tool.pyguard.ignores]
require_reason = false
disallow = ["TYP001"]
max_per_file = 10
"""
    )
    return config_path


@pytest.fixture
def empty_pyproject(tmp_path: Path) -> Path:
    """Create a pyproject.toml without [tool.pyguard] section."""
    config_path: Path = tmp_path / "pyproject.toml"
    config_path.write_text(
        """
[project]
name = "test-project"
version = "0.1.0"
"""
    )
    return config_path


@pytest.fixture
def invalid_toml(tmp_path: Path) -> Path:
    """Create an invalid TOML file."""
    config_path: Path = tmp_path / "pyproject.toml"
    config_path.write_text("invalid [ toml content")
    return config_path


@pytest.fixture
def invalid_config(tmp_path: Path) -> Path:
    """Create a pyproject.toml with invalid pyguard config."""
    config_path: Path = tmp_path / "pyproject.toml"
    config_path.write_text(
        """
[tool.pyguard]
output_format = "invalid_format"
color = "maybe"

[tool.pyguard.rules]
TYP001 = "super_error"

[tool.pyguard.ignores]
disallow = ["FAKE001"]
"""
    )
    return config_path
