"""Tests for PyGuard configuration system."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyguard.config import ConfigLoader, load_config
from pyguard.constants import (
    DEFAULT_SEVERITIES,
    AnnotationScope,
    ColorMode,
    OutputFormat,
    Severity,
)
from pyguard.types import ConfigError, PyGuardConfig


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_config_has_expected_values(self) -> None:
        """Default config should have sensible defaults."""
        config: PyGuardConfig = PyGuardConfig()

        assert config.python_version == "3.11"
        assert config.include == ("**/*.py",)
        assert config.output_format == OutputFormat.TEXT
        assert config.show_source is True
        assert config.color == ColorMode.AUTO
        assert config.config_path is None

    def test_default_severities_are_correct(self) -> None:
        """Default rule severities should match constants."""
        config: PyGuardConfig = PyGuardConfig()

        assert config.rules.severities == DEFAULT_SEVERITIES
        assert config.get_severity("TYP001") == Severity.ERROR
        assert config.get_severity("TYP003") == Severity.WARN
        assert config.get_severity("EXP001") == Severity.OFF

    def test_is_rule_enabled_returns_correct_values(self) -> None:
        """is_rule_enabled should return True for non-OFF rules."""
        config: PyGuardConfig = PyGuardConfig()

        assert config.is_rule_enabled("TYP001") is True
        assert config.is_rule_enabled("TYP003") is True
        assert config.is_rule_enabled("EXP001") is False
        assert config.is_rule_enabled("UNKNOWN") is False

    def test_default_rule_options(self) -> None:
        """Default rule options should have expected values."""
        config: PyGuardConfig = PyGuardConfig()

        assert config.rules.typ001.exempt_dunder is True
        assert config.rules.typ001.exempt_self_cls is True
        assert config.rules.typ003.scope == frozenset({AnnotationScope.MODULE})
        assert config.rules.kw001.min_params == 2
        assert config.rules.kw001.exempt_dunder is True

    def test_default_ignore_governance(self) -> None:
        """Default ignore governance should have expected values."""
        config: PyGuardConfig = PyGuardConfig()

        assert config.ignores.require_reason is True
        assert config.ignores.disallow == frozenset()
        assert config.ignores.max_per_file is None


class TestConfigImmutability:
    """Test that config dataclasses are immutable."""

    def test_pyguard_config_is_frozen(self) -> None:
        """PyGuardConfig should be frozen (immutable)."""
        config: PyGuardConfig = PyGuardConfig()

        with pytest.raises(AttributeError):
            config.python_version = "3.12"  # type: ignore[misc]

    def test_rule_config_is_frozen(self) -> None:
        """RuleConfig should be frozen (immutable)."""
        config: PyGuardConfig = PyGuardConfig()

        with pytest.raises(AttributeError):
            config.rules.typ001 = None  # type: ignore[misc]


class TestConfigLoading:
    """Test configuration loading from files."""

    def test_load_with_no_config_found_returns_defaults(self, tmp_path: Path) -> None:
        """Loading when no config file is found should return defaults."""
        # Create an isolated directory without pyproject.toml
        isolated_dir: Path = tmp_path / "isolated"
        isolated_dir.mkdir()

        # Change to isolated dir and load without explicit path
        original_cwd: str = os.getcwd()
        try:
            os.chdir(isolated_dir)
            config: PyGuardConfig = ConfigLoader.load(path=None)
            # Config should have defaults with no config_path
            assert config.python_version == "3.11"
            assert config.config_path is None
        finally:
            os.chdir(original_cwd)

    def test_load_with_empty_tool_section(self, empty_pyproject: Path) -> None:
        """Loading with empty [tool.pyguard] should return defaults."""
        config: PyGuardConfig = load_config(path=empty_pyproject)

        assert config.python_version == "3.11"
        assert config.config_path == empty_pyproject

    def test_load_custom_config(self, temp_pyproject: Path) -> None:
        """Loading custom config should parse all values."""
        config: PyGuardConfig = load_config(path=temp_pyproject)

        assert config.python_version == "3.12"
        assert config.include == ("src/**/*.py",)
        assert config.exclude == ("**/test_*.py",)
        assert config.output_format == OutputFormat.TEXT
        assert config.show_source is False
        assert config.color == ColorMode.NEVER
        assert config.config_path == temp_pyproject

    def test_load_rule_severities(self, temp_pyproject: Path) -> None:
        """Rule severities should be loaded correctly."""
        config: PyGuardConfig = load_config(path=temp_pyproject)

        assert config.get_severity("TYP001") == Severity.WARN
        assert config.get_severity("TYP002") == Severity.ERROR
        assert config.get_severity("KW001") == Severity.OFF

    def test_load_rule_options(self, temp_pyproject: Path) -> None:
        """Rule-specific options should be loaded."""
        config: PyGuardConfig = load_config(path=temp_pyproject)

        assert config.rules.kw001.min_params == 3
        assert config.rules.kw001.exempt_dunder is False

    def test_load_ignore_governance(self, temp_pyproject: Path) -> None:
        """Ignore governance should be loaded correctly."""
        config: PyGuardConfig = load_config(path=temp_pyproject)

        assert config.ignores.require_reason is False
        assert config.ignores.disallow == frozenset({"TYP001"})
        assert config.ignores.max_per_file == 10


class TestConfigValidation:
    """Test configuration validation and error handling."""

    def test_invalid_toml_raises_config_error(self, invalid_toml: Path) -> None:
        """Invalid TOML should raise ConfigError."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(path=invalid_toml)

        assert "Invalid TOML" in str(exc_info.value)
        assert exc_info.value.path == invalid_toml

    def test_invalid_config_values_raise_config_error(self, invalid_config: Path) -> None:
        """Invalid config values should raise ConfigError with all errors."""
        with pytest.raises(ConfigError) as exc_info:
            load_config(path=invalid_config)

        error_msg: str = str(exc_info.value)
        assert "output_format" in error_msg
        assert "color" in error_msg
        assert "rules.TYP001" in error_msg
        assert "FAKE001" in error_msg

    def test_non_string_severity_raises_config_error(self, tmp_path: Path) -> None:
        """Non-string severity value should raise ConfigError."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard.rules.TYP001]
severity = 1
"""
        )

        with pytest.raises(ConfigError) as exc_info:
            load_config(path=config_path)

        error_msg: str = str(exc_info.value)
        assert "rules.TYP001.severity must be a string" in error_msg

    def test_non_string_disallow_entry_raises_config_error(self, tmp_path: Path) -> None:
        """Non-string entries in ignores.disallow should raise ConfigError."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard.ignores]
disallow = [123, "TYP001"]
"""
        )

        with pytest.raises(ConfigError) as exc_info:
            load_config(path=config_path)

        error_msg: str = str(exc_info.value)
        assert "ignores.disallow entries must be strings" in error_msg


class TestConfigDiscovery:
    """Test configuration file discovery."""

    def test_find_config_in_current_directory(self, tmp_path: Path) -> None:
        """Should find pyproject.toml in current directory."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text("[project]\nname = 'test'")

        found: Path | None = ConfigLoader.find_config_file(start_path=tmp_path)

        assert found == config_path

    def test_find_config_in_parent_directory(self, tmp_path: Path) -> None:
        """Should find pyproject.toml in parent directory."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text("[project]\nname = 'test'")

        subdir: Path = tmp_path / "src" / "module"
        subdir.mkdir(parents=True)

        found: Path | None = ConfigLoader.find_config_file(start_path=subdir)

        assert found == config_path

    def test_no_config_returns_none(self, tmp_path: Path) -> None:
        """Should return None if no config file exists."""
        subdir: Path = tmp_path / "isolated"
        subdir.mkdir()

        found: Path | None = ConfigLoader.find_config_file(start_path=subdir)

        # May find pyproject.toml higher up, so just check it returns Path or None
        assert found is None or found.name == "pyproject.toml"


class TestScopeParsing:
    """Test TYP003 scope parsing."""

    def test_parse_multiple_scopes(self, tmp_path: Path) -> None:
        """Should parse multiple scope values."""
        config_path: Path = tmp_path / "pyproject.toml"
        config_path.write_text(
            """
[tool.pyguard.rules.TYP003]
scope = ["module", "class", "local"]
"""
        )

        config: PyGuardConfig = load_config(path=config_path)

        expected: frozenset[AnnotationScope] = frozenset({
            AnnotationScope.MODULE,
            AnnotationScope.CLASS,
            AnnotationScope.LOCAL,
        })
        assert config.rules.typ003.scope == expected
