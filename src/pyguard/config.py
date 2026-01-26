"""Configuration loading and validation for PyGuard."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pyguard.constants import (
    DEFAULT_EXCLUDES,
    DEFAULT_SEVERITIES,
    RULE_CODES,
    AnnotationScope,
    ColorMode,
    OutputFormat,
    Severity,
)
from pyguard.types import (
    ConfigError,
    IgnoreGovernance,
    KW001Options,
    PyGuardConfig,
    RuleConfig,
    TYP001Options,
    TYP003Options,
)


class ConfigLoader:
    """Loads and validates PyGuard configuration."""

    @staticmethod
    def find_config_file(start_path: Path | None = None) -> Path | None:
        """
        Find pyproject.toml by walking up from start_path.

        Args:
            start_path: Directory to start searching from. Defaults to cwd.

        Returns:
            Path to pyproject.toml if found, None otherwise.
        """
        if start_path is None:
            start_path = Path.cwd()

        start_path = start_path.resolve()

        for directory in [start_path, *start_path.parents]:
            config_path: Path = directory / "pyproject.toml"
            if config_path.is_file():
                return config_path

        return None

    @staticmethod
    def load(path: Path | None = None) -> PyGuardConfig:
        """
        Load configuration from pyproject.toml.

        Args:
            path: Explicit path to pyproject.toml. If None, searches upward.

        Returns:
            Validated PyGuardConfig instance.

        Raises:
            ConfigError: If configuration is invalid.
        """
        if path is None:
            path = ConfigLoader.find_config_file()

        if path is None:
            return PyGuardConfig()

        try:
            with open(path, "rb") as f:
                data: dict[str, Any] = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"Invalid TOML: {e}", path=path) from e
        except OSError as e:
            raise ConfigError(f"Cannot read config file: {e}", path=path) from e

        tool_config: dict[str, Any] = data.get("tool", {}).get("pyguard", {})

        return ConfigLoader._parse_config(tool_config, config_path=path)

    @staticmethod
    def _parse_config(
        data: dict[str, Any],
        *,
        config_path: Path | None = None,
    ) -> PyGuardConfig:
        """Parse and validate configuration dictionary."""
        errors: list[str] = []

        # Parse python_version
        python_version: str = data.get("python_version", "3.11")
        if not isinstance(python_version, str):
            errors.append(
                f"python_version must be a string, got {type(python_version).__name__}"
            )

        # Parse include patterns
        include: tuple[str, ...] = ("**/*.py",)
        raw_include: Any = data.get("include", ("**/*.py",))
        if isinstance(raw_include, list):
            include = tuple(raw_include)
        elif not isinstance(raw_include, tuple):
            errors.append(f"include must be a list, got {type(raw_include).__name__}")

        # Parse exclude patterns
        exclude: tuple[str, ...] = DEFAULT_EXCLUDES
        raw_exclude: Any = data.get("exclude", DEFAULT_EXCLUDES)
        if isinstance(raw_exclude, list):
            exclude = tuple(raw_exclude)
        elif not isinstance(raw_exclude, tuple):
            errors.append(f"exclude must be a list, got {type(raw_exclude).__name__}")

        # Parse output_format
        output_format: OutputFormat = OutputFormat.TEXT
        if "output_format" in data:
            try:
                output_format = OutputFormat(data["output_format"])
            except ValueError:
                valid: list[str] = [f.value for f in OutputFormat]
                errors.append(f"output_format must be one of {valid}")

        # Parse show_source
        show_source: bool = data.get("show_source", True)
        if not isinstance(show_source, bool):
            errors.append("show_source must be a boolean")
            show_source = True

        # Parse color
        color: ColorMode = ColorMode.AUTO
        if "color" in data:
            try:
                color = ColorMode(data["color"])
            except ValueError:
                valid = [c.value for c in ColorMode]
                errors.append(f"color must be one of {valid}")

        # Parse rules
        rules: RuleConfig = ConfigLoader._parse_rules(data.get("rules", {}), errors)

        # Parse ignores
        ignores: IgnoreGovernance = ConfigLoader._parse_ignores(
            data.get("ignores", {}), errors
        )

        if errors:
            error_msg: str = "Configuration errors:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            raise ConfigError(error_msg, path=config_path)

        return PyGuardConfig(
            config_path=config_path,
            python_version=python_version,
            include=include,
            exclude=exclude,
            output_format=output_format,
            show_source=show_source,
            color=color,
            rules=rules,
            ignores=ignores,
        )

    @staticmethod
    def _parse_rules(data: dict[str, Any], errors: list[str]) -> RuleConfig:
        """Parse rules configuration."""
        severities: dict[str, Severity] = dict(DEFAULT_SEVERITIES)

        for key, value in data.items():
            if key.upper() in RULE_CODES:
                rule_code: str = key.upper()
                if isinstance(value, str):
                    try:
                        severities[rule_code] = Severity(value.lower())
                    except ValueError:
                        valid: list[str] = [s.value for s in Severity]
                        errors.append(f"rules.{key} must be one of {valid}")
                elif isinstance(value, dict) and "severity" in value:
                    try:
                        severities[rule_code] = Severity(value["severity"].lower())
                    except ValueError:
                        valid = [s.value for s in Severity]
                        errors.append(f"rules.{key}.severity must be one of {valid}")

        # Parse TYP001 options
        typ001_data: dict[str, Any] = data.get("TYP001", {})
        typ001: TYP001Options
        if isinstance(typ001_data, dict):
            typ001 = TYP001Options(
                exempt_dunder=typ001_data.get("exempt_dunder", True),
                exempt_self_cls=typ001_data.get("exempt_self_cls", True),
            )
        else:
            typ001 = TYP001Options()

        # Parse TYP003 options
        typ003_data: dict[str, Any] = data.get("TYP003", {})
        typ003: TYP003Options
        if isinstance(typ003_data, dict):
            scope_values: list[str] = typ003_data.get("scope", ["module"])
            scope: frozenset[AnnotationScope]
            if isinstance(scope_values, list):
                try:
                    scope = frozenset(AnnotationScope(s) for s in scope_values)
                except ValueError:
                    valid = [s.value for s in AnnotationScope]
                    errors.append(f"rules.TYP003.scope values must be from {valid}")
                    scope = frozenset({AnnotationScope.MODULE})
            else:
                scope = frozenset({AnnotationScope.MODULE})
            typ003 = TYP003Options(scope=scope)
        else:
            typ003 = TYP003Options()

        # Parse KW001 options
        kw001_data: dict[str, Any] = data.get("KW001", {})
        kw001: KW001Options
        if isinstance(kw001_data, dict):
            kw001 = KW001Options(
                min_params=kw001_data.get("min_params", 2),
                exempt_dunder=kw001_data.get("exempt_dunder", True),
                exempt_private=kw001_data.get("exempt_private", True),
                exempt_overrides=kw001_data.get("exempt_overrides", True),
            )
        else:
            kw001 = KW001Options()

        return RuleConfig(
            severities=severities,
            typ001=typ001,
            typ003=typ003,
            kw001=kw001,
        )

    @staticmethod
    def _parse_ignores(data: dict[str, Any], errors: list[str]) -> IgnoreGovernance:
        """Parse ignore governance configuration."""
        require_reason: bool = data.get("require_reason", True)
        if not isinstance(require_reason, bool):
            errors.append("ignores.require_reason must be a boolean")
            require_reason = True

        raw_disallow: Any = data.get("disallow", [])
        disallow: frozenset[str]
        if isinstance(raw_disallow, list):
            invalid_codes: list[str] = [
                c for c in raw_disallow if c.upper() not in RULE_CODES
            ]
            if invalid_codes:
                errors.append(
                    f"ignores.disallow contains unknown rule codes: {invalid_codes}"
                )
            disallow = frozenset(
                c.upper() for c in raw_disallow if c.upper() in RULE_CODES
            )
        else:
            errors.append("ignores.disallow must be a list")
            disallow = frozenset()

        max_per_file: int | None = data.get("max_per_file")
        if max_per_file is not None and not isinstance(max_per_file, int):
            errors.append("ignores.max_per_file must be an integer or null")
            max_per_file = None

        return IgnoreGovernance(
            require_reason=require_reason,
            disallow=disallow,
            max_per_file=max_per_file,
        )


def load_config(path: Path | None = None) -> PyGuardConfig:
    """
    Convenience function to load configuration.

    Args:
        path: Optional explicit path to pyproject.toml.

    Returns:
        Validated configuration.
    """
    return ConfigLoader.load(path)
