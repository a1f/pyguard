"""Common types and dataclasses for PyGuard."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

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
    disallow: frozenset[str] = field(default_factory=lambda: frozenset())
    max_per_file: int | None = None


@dataclass(frozen=True, slots=True)
class RuleConfig:
    """Configuration for all rules."""

    severities: MappingProxyType[str, Severity] = field(
        default_factory=lambda: MappingProxyType(DEFAULT_SEVERITIES)
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
