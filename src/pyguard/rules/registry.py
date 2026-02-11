"""Rule registry for PyGuard."""
from __future__ import annotations

from pyguard.rules.base import Rule
from pyguard.rules.typ001 import TYP001Rule
from pyguard.types import PyGuardConfig


def get_enabled_rules(*, config: PyGuardConfig) -> list[Rule]:
    """Return rule instances that are not OFF in the given config."""
    all_rules: list[Rule] = _all_rules()
    return [rule for rule in all_rules if config.is_rule_enabled(rule.code)]


def _all_rules() -> list[Rule]:
    """Return all registered rule instances."""
    rules: list[Rule] = [
        TYP001Rule(),
    ]
    return rules
