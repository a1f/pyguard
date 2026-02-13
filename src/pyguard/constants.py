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

SYNTAX_ERROR_CODE: Final[str] = "SYN001"

IGN001_CODE: Final[str] = "IGN001"
IGN002_CODE: Final[str] = "IGN002"
IGN003_CODE: Final[str] = "IGN003"

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
