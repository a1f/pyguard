"""Rule protocol for PyGuard lint rules."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pyguard.diagnostics import Diagnostic
from pyguard.parser import ParseResult
from pyguard.types import PyGuardConfig


@runtime_checkable
class Rule(Protocol):
    """Structural interface for lint rules."""

    @property
    def code(self) -> str: ...

    def check(
        self,
        *,
        parse_result: ParseResult,
        config: PyGuardConfig,
    ) -> list[Diagnostic]: ...
