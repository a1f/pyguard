"""Pipeline for chaining multiple fixers on a single source string."""

from __future__ import annotations

from pyguard.fixers.imp001 import fix_local_imports
from pyguard.fixers.typ002 import fix_missing_return_none
from pyguard.fixers.typ003 import fix_missing_variable_annotations
from pyguard.fixers.typ010 import fix_legacy_typing


def fix_all(source: str) -> str:
    """Apply all str-to-str fixers in dependency order.

    Order matters:
    1. TYP010 — modernize typing syntax, may remove imports (changes line count)
    2. IMP001 — move in-function imports to module level
    3. TYP002 — add ``-> None`` to trivial functions
    4. TYP003 — add variable type annotations
    """
    source = fix_legacy_typing(source)
    source = fix_local_imports(source)
    source = fix_missing_return_none(source)
    source = fix_missing_variable_annotations(source)
    return source
