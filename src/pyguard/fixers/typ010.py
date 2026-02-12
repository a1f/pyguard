"""TYP010 fixer: Modernize legacy typing syntax using LibCST."""
from __future__ import annotations

try:
    import libcst as cst

    _HAS_LIBCST: bool = True
except ImportError:
    _HAS_LIBCST = False

_BUILTIN_REPLACEMENTS: dict[str, str] = {
    "List": "list",
    "Dict": "dict",
    "Tuple": "tuple",
    "Set": "set",
    "FrozenSet": "frozenset",
    "Type": "type",
}

_LEGACY_NAMES: frozenset[str] = frozenset(
    {"Optional", "Union"} | _BUILTIN_REPLACEMENTS.keys()
)


def fix_legacy_typing(source: str) -> str:
    """Replace legacy ``typing`` constructs with modern Python 3.11+ syntax.

    Transforms:
    - ``Optional[T]`` → ``T | None``
    - ``Union[A, B]`` → ``A | B``
    - ``List[T]`` → ``list[T]``, ``Dict[K, V]`` → ``dict[K, V]``, etc.

    Also removes typing imports that become unused after the transformation.
    Returns the source unchanged if libcst is not installed or on parse error.
    """
    if not _HAS_LIBCST:
        return source
    if not source.strip():
        return source

    try:
        tree: cst.Module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return source

    collector: _ImportCollector = _ImportCollector()
    tree.visit(collector)

    if not collector.legacy_names:
        return source

    transformer: _LegacyTypingTransformer = _LegacyTypingTransformer(
        legacy_names=collector.legacy_names,
    )
    new_tree: cst.Module = tree.visit(transformer)

    if not transformer.changed:
        return source

    cleaner: _ImportCleaner = _ImportCleaner(
        removable=collector.legacy_names,
    )
    new_tree = new_tree.visit(cleaner)

    result: str = new_tree.code
    # Strip leading blank lines left after removing import statements
    return result.lstrip("\n")


class _ImportCollector(cst.CSTTransformer):
    """Collect names imported from ``typing`` that are legacy constructs.

    Extends CSTTransformer (returning nodes unchanged) so it can be used
    with ``Module.visit()``.
    """

    def __init__(self) -> None:
        self.legacy_names: set[str] = set()

    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        if not _is_typing_module(node):
            return True
        if isinstance(node.names, cst.ImportStar):
            return True
        for alias in node.names:
            name: str = _alias_imported_name(alias)
            local: str = _alias_local_name(alias)
            if name in _LEGACY_NAMES:
                self.legacy_names.add(local)
        return True


class _LegacyTypingTransformer(cst.CSTTransformer):
    """Transform legacy typing subscripts to modern syntax."""

    def __init__(self, *, legacy_names: set[str]) -> None:
        self._legacy_names: set[str] = legacy_names
        self.changed: bool = False

    def leave_Subscript(
        self,
        original_node: cst.Subscript,
        updated_node: cst.Subscript,
    ) -> cst.BaseExpression:
        name: str | None = _get_subscript_legacy_name(
            updated_node, self._legacy_names
        )
        if name is None:
            return updated_node

        elements: list[cst.BaseExpression] = _extract_slice_elements(
            updated_node
        )

        if name == "Optional":
            if len(elements) != 1:
                return updated_node
            self.changed = True
            return _make_bitor(elements[0], cst.Name("None"))

        if name == "Union":
            if not elements:
                return updated_node
            self.changed = True
            return _join_bitor(elements)

        if name in _BUILTIN_REPLACEMENTS:
            self.changed = True
            replacement: str = _BUILTIN_REPLACEMENTS[name]
            return updated_node.with_changes(value=cst.Name(replacement))

        return updated_node


class _ImportCleaner(cst.CSTTransformer):
    """Remove typing imports that are no longer used after transformation."""

    def __init__(self, *, removable: set[str]) -> None:
        self._removable: set[str] = removable

    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        if not _is_typing_module(updated_node):
            return updated_node
        if isinstance(updated_node.names, cst.ImportStar):
            return updated_node

        kept: list[cst.ImportAlias] = []
        for alias in updated_node.names:
            name: str = _alias_imported_name(alias)
            if name not in self._removable:
                kept.append(alias)

        if not kept:
            return cst.RemovalSentinel.REMOVE

        # Strip trailing comma from last kept import
        cleaned: list[cst.ImportAlias] = list(kept)
        cleaned[-1] = cleaned[-1].with_changes(
            comma=cst.MaybeSentinel.DEFAULT
        )

        return updated_node.with_changes(names=cleaned)


def _is_typing_module(node: cst.ImportFrom) -> bool:
    """Check if an ImportFrom is ``from typing import ...``."""
    if isinstance(node.module, cst.Name):
        return node.module.value == "typing"
    return False


def _alias_imported_name(alias: cst.ImportAlias) -> str:
    """Get the original imported name from an ImportAlias."""
    if isinstance(alias.name, cst.Name):
        return alias.name.value
    return ""


def _alias_local_name(alias: cst.ImportAlias) -> str:
    """Get the local name (after ``as``) from an ImportAlias."""
    if (
        alias.asname
        and isinstance(alias.asname, cst.AsName)
        and isinstance(alias.asname.name, cst.Name)
    ):
        return alias.asname.name.value
    return _alias_imported_name(alias)


def _get_subscript_legacy_name(
    node: cst.Subscript, legacy_names: set[str]
) -> str | None:
    """Return the legacy name if node is a legacy typing subscript."""
    if isinstance(node.value, cst.Name) and node.value.value in legacy_names:
        return node.value.value
    return None


def _extract_slice_elements(
    node: cst.Subscript,
) -> list[cst.BaseExpression]:
    """Extract the type arguments from a subscript."""
    elements: list[cst.BaseExpression] = []
    for s in node.slice:
        if isinstance(s, cst.SubscriptElement) and isinstance(
            s.slice, cst.Index
        ):
            elements.append(s.slice.value)
    return elements


def _make_bitor(
    left: cst.BaseExpression, right: cst.BaseExpression
) -> cst.BinaryOperation:
    """Create ``left | right`` with proper spacing."""
    return cst.BinaryOperation(
        left=left,
        operator=cst.BitOr(
            whitespace_before=cst.SimpleWhitespace(" "),
            whitespace_after=cst.SimpleWhitespace(" "),
        ),
        right=right,
    )


def _join_bitor(
    elements: list[cst.BaseExpression],
) -> cst.BaseExpression:
    """Join multiple expressions with ``|``."""
    result: cst.BaseExpression = elements[0]
    for elem in elements[1:]:
        result = _make_bitor(result, elem)
    return result
