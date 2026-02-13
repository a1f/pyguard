"""Rule registry for PyGuard."""
from __future__ import annotations

from pyguard.rules.base import Rule
from pyguard.rules.imp001 import IMP001Rule
from pyguard.rules.kw001 import KW001Rule
from pyguard.rules.ret001 import RET001Rule
from pyguard.rules.typ001 import TYP001Rule
from pyguard.rules.typ002 import TYP002Rule
from pyguard.rules.typ003 import TYP003Rule
from pyguard.rules.typ010 import TYP010Rule
from pyguard.types import PyGuardConfig


def get_enabled_rules(*, config: PyGuardConfig) -> list[Rule]:
    """Return rule instances that are not OFF in the given config."""
    all_rules: list[Rule] = _all_rules()
    return [rule for rule in all_rules if config.is_rule_enabled(rule.code)]


def _all_rules() -> list[Rule]:
    """Return all registered rule instances."""
    rules: list[Rule] = [
        TYP001Rule(),
        TYP002Rule(),
        TYP003Rule(),
        TYP010Rule(),
        KW001Rule(),
        IMP001Rule(),
        RET001Rule(),
    ]
    return rules
