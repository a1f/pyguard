# Step 1: Configuration System - Implementation Plan

## Overview

Implement a complete configuration system for PyGuard that loads settings from `pyproject.toml`, validates them, and makes them available to the CLI and linting engine.

**Exit Criteria**: `pyguard lint` reads config and prints resolved settings.

**Note**: Since Step 0 (Repository Bootstrap) was not completed, this step includes the necessary project structure setup.

---

## 1. Project Structure

```
pyguard/
├── pyproject.toml          # Project metadata + [tool.pyguard] schema
├── src/
│   └── pyguard/
│       ├── __init__.py     # Empty (package marker only)
│       ├── __main__.py     # Enable `python -m pyguard`
│       ├── cli.py          # CLI entry point (click)
│       ├── config.py       # Config loading logic
│       ├── constants.py    # Rule codes, default values, enums
│       └── types.py        # Common types and dataclasses
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── test_config.py      # Config system tests
│   └── test_cli.py         # CLI integration tests
└── README.md
```

---

## 2. pyproject.toml

### 2.1 Project Metadata

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyguard"
version = "0.1.0"
description = "A strict Python linter enforcing typing, keyword-only APIs, and structured returns"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Alex Fetisov" }
]
keywords = ["linter", "typing", "python", "static-analysis"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Quality Assurance",
    "Typing :: Typed",
]
dependencies = [
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1",
]

[project.scripts]
pyguard = "pyguard.cli:main"
```

### 2.2 Tool Configuration (for development)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --tb=short"
```

---

## 3. [tool.pyguard] Configuration Schema

This is what users will configure in their projects:

```toml
[tool.pyguard]
# Target Python version (affects which rules apply)
python_version = "3.11"

# File discovery
include = ["src/**/*.py", "tests/**/*.py"]  # Glob patterns to include
exclude = [                                  # Glob patterns to exclude
    "**/__pycache__/**",
    "**/.*",
    "build/**",
    "dist/**",
]

# Output settings
output_format = "text"  # "text" | "json" | "github"
show_source = true      # Show source code snippet in output
color = "auto"          # "auto" | "always" | "never"

# Rule severities: "error" | "warn" | "off"
[tool.pyguard.rules]
TYP001 = "error"   # Missing function parameter annotations
TYP002 = "error"   # Missing function return annotation
TYP003 = "warn"    # Missing variable annotation
TYP010 = "error"   # Disallow legacy typing syntax
KW001 = "warn"     # Require keyword-only parameters
RET001 = "warn"    # Disallow heterogeneous tuple returns
IMP001 = "error"   # Disallow imports inside function bodies
EXP001 = "off"     # Structured return types must be module-level
EXP002 = "off"     # Enforce __all__ or explicit re-export policy

# Rule-specific options
[tool.pyguard.rules.TYP001]
exempt_dunder = true              # Exempt __init__, __str__, etc.
exempt_self_cls = true            # Don't require annotation for self/cls

[tool.pyguard.rules.TYP003]
scope = ["module"]  # "module" | "class" | "local" - which scopes to check

[tool.pyguard.rules.KW001]
min_params = 2                    # Only enforce for functions with >= N params
exempt_dunder = true              # Exempt __init__, __new__, etc.
exempt_private = true             # Exempt _private functions
exempt_overrides = true           # Exempt methods with @override decorator

# Ignore governance
[tool.pyguard.ignores]
require_reason = true             # Require "because: ..." in ignore comments
disallow = []                     # Rule codes that cannot be ignored
max_per_file = null               # Maximum ignores per file (null = unlimited)
```

---

## 4. Constants Module (constants.py)

```python
"""Constants and enums for PyGuard configuration."""
from __future__ import annotations

from enum import Enum
from typing import Final

__version__: Final[str] = "0.1.0"


class Severity(Enum):
    """Rule severity levels."""

    ERROR = "error"
    WARN = "warn"
    OFF = "off"


class OutputFormat(Enum):
    """Output format options."""

    TEXT = "text"
    JSON = "json"
    GITHUB = "github"


class ColorMode(Enum):
    """Color output modes."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class AnnotationScope(Enum):
    """Variable annotation enforcement scope."""

    MODULE = "module"
    CLASS = "class"
    LOCAL = "local"


RULE_CODES: Final[frozenset[str]] = frozenset({
    "TYP001",  # Missing function parameter annotations
    "TYP002",  # Missing function return annotation
    "TYP003",  # Missing variable annotation
    "TYP010",  # Disallow legacy typing syntax
    "KW001",   # Require keyword-only parameters
    "RET001",  # Disallow heterogeneous tuple returns
    "IMP001",  # Disallow imports inside function bodies
    "EXP001",  # Structured return types must be module-level
    "EXP002",  # Enforce __all__ or explicit re-export policy
})

DEFAULT_SEVERITIES: Final[dict[str, Severity]] = {
    "TYP001": Severity.ERROR,
    "TYP002": Severity.ERROR,
    "TYP003": Severity.WARN,
    "TYP010": Severity.ERROR,
    "KW001": Severity.WARN,
    "RET001": Severity.WARN,
    "IMP001": Severity.ERROR,
    "EXP001": Severity.OFF,
    "EXP002": Severity.OFF,
}

DEFAULT_EXCLUDES: Final[tuple[str, ...]] = (
    "**/__pycache__/**",
    "**/.*",
    "**/.git/**",
    "**/.venv/**",
    "**/venv/**",
    "**/env/**",
    "build/**",
    "dist/**",
    "*.egg-info/**",
)
```

---

## 5. Types Module (types.py)

```python
"""Common types and dataclasses for PyGuard."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pyguard.constants import (
    DEFAULT_EXCLUDES,
    DEFAULT_SEVERITIES,
    AnnotationScope,
    ColorMode,
    OutputFormat,
    Severity,
)


@dataclass(frozen=True, slots=True)
class TYP001Options:
    """Options for TYP001 (parameter annotation) rule."""

    exempt_dunder: bool = True
    exempt_self_cls: bool = True


@dataclass(frozen=True, slots=True)
class TYP003Options:
    """Options for TYP003 (variable annotation) rule."""

    scope: frozenset[AnnotationScope] = field(
        default_factory=lambda: frozenset({AnnotationScope.MODULE})
    )


@dataclass(frozen=True, slots=True)
class KW001Options:
    """Options for KW001 (keyword-only parameters) rule."""

    min_params: int = 2
    exempt_dunder: bool = True
    exempt_private: bool = True
    exempt_overrides: bool = True


@dataclass(frozen=True, slots=True)
class IgnoreGovernance:
    """Configuration for ignore/skip governance."""

    require_reason: bool = True
    disallow: frozenset[str] = field(default_factory=frozenset)
    max_per_file: int | None = None


@dataclass(frozen=True, slots=True)
class RuleConfig:
    """Configuration for all rules."""

    severities: dict[str, Severity] = field(
        default_factory=lambda: dict(DEFAULT_SEVERITIES)
    )
    typ001: TYP001Options = field(default_factory=TYP001Options)
    typ003: TYP003Options = field(default_factory=TYP003Options)
    kw001: KW001Options = field(default_factory=KW001Options)


@dataclass(frozen=True, slots=True)
class PyGuardConfig:
    """Complete PyGuard configuration."""

    config_path: Path | None = None
    python_version: str = "3.11"
    include: tuple[str, ...] = ("**/*.py",)
    exclude: tuple[str, ...] = DEFAULT_EXCLUDES
    output_format: OutputFormat = OutputFormat.TEXT
    show_source: bool = True
    color: ColorMode = ColorMode.AUTO
    rules: RuleConfig = field(default_factory=RuleConfig)
    ignores: IgnoreGovernance = field(default_factory=IgnoreGovernance)

    def get_severity(self, rule_code: str) -> Severity:
        """Get the severity for a rule code."""
        return self.rules.severities.get(rule_code, Severity.OFF)

    def is_rule_enabled(self, rule_code: str) -> bool:
        """Check if a rule is enabled (not OFF)."""
        return self.get_severity(rule_code) != Severity.OFF


class ConfigError(Exception):
    """Error during configuration loading or validation."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        self.path: Path | None = path
        super().__init__(message)
```

---

## 6. Config Loading (config.py)

```python
"""Configuration loading and validation for PyGuard."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pyguard.constants import (
    RULE_CODES,
    AnnotationScope,
    ColorMode,
    DEFAULT_EXCLUDES,
    DEFAULT_SEVERITIES,
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
                elif isinstance(value, dict):
                    if "severity" in value:
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
```

---

## 7. CLI Structure (cli.py) - Using Click

```python
"""Command-line interface for PyGuard using Click."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import click

from pyguard.config import load_config
from pyguard.constants import __version__, ColorMode, OutputFormat
from pyguard.types import ConfigError, PyGuardConfig


def format_config_text(config: PyGuardConfig) -> str:
    """Format configuration as human-readable text."""
    lines: list[str] = [
        "PyGuard Configuration",
        "=" * 40,
        "",
        f"Config file: {config.config_path or '(defaults)'}",
        f"Python version: {config.python_version}",
        "",
        "File Discovery:",
        f"  Include: {', '.join(config.include)}",
        f"  Exclude: {', '.join(config.exclude[:5])}{'...' if len(config.exclude) > 5 else ''}",
        "",
        "Output:",
        f"  Format: {config.output_format.value}",
        f"  Color: {config.color.value}",
        f"  Show source: {config.show_source}",
        "",
        "Rule Severities:",
    ]

    for code, severity in sorted(config.rules.severities.items()):
        status: str = severity.value.upper()
        lines.append(f"  {code}: {status}")

    lines.extend([
        "",
        "Ignore Governance:",
        f"  Require reason: {config.ignores.require_reason}",
        f"  Disallow: {sorted(config.ignores.disallow) or '(none)'}",
        f"  Max per file: {config.ignores.max_per_file or 'unlimited'}",
    ])

    return "\n".join(lines)


def format_config_json(config: PyGuardConfig) -> str:
    """Format configuration as JSON."""
    data: dict[str, Any] = {
        "config_path": str(config.config_path) if config.config_path else None,
        "python_version": config.python_version,
        "include": list(config.include),
        "exclude": list(config.exclude),
        "output_format": config.output_format.value,
        "show_source": config.show_source,
        "color": config.color.value,
        "rules": {
            "severities": {
                code: sev.value for code, sev in config.rules.severities.items()
            },
            "TYP001": {
                "exempt_dunder": config.rules.typ001.exempt_dunder,
                "exempt_self_cls": config.rules.typ001.exempt_self_cls,
            },
            "TYP003": {
                "scope": [s.value for s in config.rules.typ003.scope],
            },
            "KW001": {
                "min_params": config.rules.kw001.min_params,
                "exempt_dunder": config.rules.kw001.exempt_dunder,
                "exempt_private": config.rules.kw001.exempt_private,
                "exempt_overrides": config.rules.kw001.exempt_overrides,
            },
        },
        "ignores": {
            "require_reason": config.ignores.require_reason,
            "disallow": sorted(config.ignores.disallow),
            "max_per_file": config.ignores.max_per_file,
        },
    }
    return json.dumps(data, indent=2)


class ConfigType(click.ParamType):
    """Custom Click parameter type for config path."""

    name = "path"

    def convert(
        self,
        value: str | Path | None,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> Path | None:
        if value is None:
            return None
        return Path(value)


pass_config = click.make_pass_decorator(PyGuardConfig)


@click.group()
@click.version_option(version=__version__, prog_name="pyguard")
@click.option(
    "--config",
    "config_path",
    type=ConfigType(),
    default=None,
    help="Path to pyproject.toml (default: search upward from current directory)",
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    """PyGuard - A strict Python linter for typing, APIs, and structured returns."""
    ctx.ensure_object(dict)
    try:
        config: PyGuardConfig = load_config(config_path)
        ctx.obj["config"] = config
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        if e.path:
            click.echo(f"  in: {e.path}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--validate", is_flag=True, help="Only validate configuration, don't print")
@click.option("--json", "as_json", is_flag=True, help="Output configuration as JSON")
@click.pass_context
def config(ctx: click.Context, validate: bool, as_json: bool) -> None:
    """Show or validate configuration."""
    cfg: PyGuardConfig = ctx.obj["config"]

    if validate:
        click.echo(f"Configuration valid: {cfg.config_path or '(defaults)'}")
        return

    if as_json:
        click.echo(format_config_json(cfg))
    else:
        click.echo(format_config_text(cfg))


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "github"]),
    default=None,
    help="Output format (overrides config)",
)
@click.option(
    "--color",
    type=click.Choice(["auto", "always", "never"]),
    default=None,
    help="Color output mode (overrides config)",
)
@click.option("--show-source/--no-show-source", default=None, help="Show source code snippets")
@click.pass_context
def lint(
    ctx: click.Context,
    paths: tuple[Path, ...],
    output_format: str | None,
    color: str | None,
    show_source: bool | None,
) -> None:
    """Run linting on Python files."""
    cfg: PyGuardConfig = ctx.obj["config"]

    # Apply CLI overrides
    overrides: dict[str, Any] = {}
    if output_format is not None:
        overrides["output_format"] = OutputFormat(output_format)
    if color is not None:
        overrides["color"] = ColorMode(color)
    if show_source is not None:
        overrides["show_source"] = show_source

    if overrides:
        cfg = replace(cfg, **overrides)

    # Default to current directory if no paths specified
    if not paths:
        paths = (Path("."),)

    # Placeholder: show that we loaded config
    click.echo(f"Would lint paths: {[str(p) for p in paths]}")
    click.echo(f"Using config from: {cfg.config_path or '(defaults)'}")
    click.echo()
    click.echo(format_config_text(cfg))


def main() -> None:
    """Main entry point for pyguard CLI."""
    cli()


if __name__ == "__main__":
    main()
```

---

## 8. Other Files

### 8.1 __init__.py (empty)

```python
# Empty - package marker only
```

### 8.2 __main__.py

```python
"""Enable running pyguard as a module: python -m pyguard."""
from pyguard.cli import main

if __name__ == "__main__":
    main()
```

---

## 9. Implementation Sequence

### Phase 1: Project Bootstrap
1. Create directory structure: `src/pyguard/`, `tests/`
2. Create `pyproject.toml` with project metadata (includes click dependency)
3. Create empty `__init__.py`, `__main__.py`
4. Verify `pip install -e .` works
5. Verify `pyguard --help` prints (minimal click CLI)

### Phase 2: Constants & Types
1. Implement `constants.py` with enums, rule codes, defaults
2. Implement `types.py` with all dataclasses
3. Write unit tests for:
   - Default values are correct
   - Dataclasses are immutable (frozen)
   - Helper methods work (`get_severity`, `is_rule_enabled`)

### Phase 3: Config Loading
1. Implement `ConfigLoader.find_config_file()`
2. Implement `ConfigLoader.load()` with TOML parsing
3. Implement `_parse_config()`, `_parse_rules()`, `_parse_ignores()`
4. Write tests for:
   - Loading with no config file (returns defaults)
   - Loading with empty [tool.pyguard] section
   - Loading with full configuration
   - Validation errors (invalid values)
   - File discovery (walking up directories)

### Phase 4: CLI
1. Implement click-based CLI in `cli.py`
2. Implement `config` command (text and JSON output)
3. Implement `lint` command (placeholder showing resolved config)
4. Wire up CLI override flags
5. Write CLI integration tests

### Phase 5: Verification
1. Run `pytest` - all tests pass
2. Run `mypy src/` - no type errors
3. Run `ruff check src/` - no lint errors
4. Verify exit criteria manually

---

## 10. Test Cases

### Config Defaults
- Default config has expected values
- Default severities are correct for each rule
- `is_rule_enabled()` returns True for enabled rules, False for OFF

### Config Loading
- No pyproject.toml returns defaults
- Empty [tool.pyguard] returns defaults
- Custom python_version is loaded
- Include/exclude patterns are loaded as tuples
- Rule severities are loaded correctly
- Rule options (TYP003.scope, KW001.min_params) are loaded
- Ignore governance is loaded

### Config Validation
- Invalid TOML syntax raises ConfigError
- Invalid output_format raises ConfigError
- Invalid severity value raises ConfigError
- Invalid scope value raises ConfigError
- Unknown rule in disallow raises ConfigError

### Config Discovery
- Finds pyproject.toml in current directory
- Finds pyproject.toml in parent directory
- Returns None if no config exists

### CLI
- `--help` shows usage
- `--version` shows version
- `config` shows resolved config
- `config --json` outputs valid JSON
- `lint` shows it loaded config
- Invalid config exits with error code 1

---

## 11. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CLI library | click | Better UX, composable, widely used |
| Config library | stdlib dataclasses | Minimal dependencies beyond click |
| TOML parsing | tomllib (stdlib) | Available in Python 3.11+ |
| Config format | pyproject.toml only | Consistency with ruff, black, mypy |
| Immutability | frozen=True, slots=True | Prevent accidental mutation |
| Validation | Collect all errors | Better UX than fail-fast |
| Defaults | Strict for typing rules | Encourage best practices |

---

## 12. Exit Criteria Verification

After implementation, verify:

```bash
# Install in development mode
pip install -e .

# Basic CLI
pyguard --help          # Shows usage
pyguard --version       # Shows 0.1.0

# Config command
pyguard config          # Shows resolved config (defaults)
pyguard config --json   # Shows JSON output
pyguard config --validate  # Validates config

# Lint command (placeholder)
pyguard lint .          # Shows "Would lint" + resolved config
pyguard lint src/       # Shows "Would lint" + resolved config

# With explicit config
pyguard --config path/to/pyproject.toml config

# Error handling
# (Create invalid config, verify error message)
```

---

## 13. Files Summary

| File | Lines (est.) | Description |
|------|--------------|-------------|
| `pyproject.toml` | 65 | Project metadata + dev tool config |
| `src/pyguard/__init__.py` | 1 | Empty package marker |
| `src/pyguard/__main__.py` | 6 | Module entry point |
| `src/pyguard/constants.py` | 70 | Enums, rule codes, defaults |
| `src/pyguard/types.py` | 100 | Dataclasses for config |
| `src/pyguard/config.py` | 200 | Config loading logic |
| `src/pyguard/cli.py` | 180 | CLI with click |
| `tests/conftest.py` | 30 | Pytest fixtures |
| `tests/test_config.py` | 200 | Config tests |
| `tests/test_cli.py` | 80 | CLI tests |

**Total**: ~930 lines of Python

---

## Next Steps

Once this plan is approved:
1. Implement Phase 1 (Bootstrap)
2. Implement Phase 2 (Constants & Types)
3. Implement Phase 3 (Config Loading)
4. Implement Phase 4 (CLI)
5. Run verification (Phase 5)
