# PyGuard Linting Rules Implementation Plan

## Overview

Implement all 9 linting rules with detection and autofix capabilities. Each rule is a separate phase with its own validation gate.

---

## Architecture: Rule Framework (Phase 0)

Before implementing individual rules, create the rule framework.

### Step 0.1: Create rule base class and registry
**Files**: `src/pyguard/rules/__init__.py`, `src/pyguard/rules/base.py`

```python
# base.py
class Rule(Protocol):
    code: str

    def check(
        self,
        *,
        parse_result: ParseResult,
        config: PyGuardConfig
    ) -> list[Diagnostic]: ...
```

### Step 0.2: Integrate rules into runner
**File**: `src/pyguard/runner.py`

Modify `lint_paths()` to:
1. Get enabled rules from registry
2. For each file: run all rules, collect diagnostics
3. Respect severity (skip if OFF)

### Step 0.3: Add rule registry
**File**: `src/pyguard/rules/__init__.py`

```python
def get_enabled_rules(config: PyGuardConfig) -> list[Rule]:
    """Return rules that are not OFF."""
```

**Validation**:
```bash
pytest tests/test_runner.py -v
mypy src/
```

---

## Phase 1: TYP001 - Missing Parameter Annotations

### Step 1.1: Implement TYP001 detection
**File**: `src/pyguard/rules/typ001.py`

AST visitor that:
- Visits `FunctionDef` and `AsyncFunctionDef`
- Checks each `arg` in `arguments` for missing `annotation`
- Respects exemptions: `self`, `cls`, dunder methods, `*args`/`**kwargs`
- Uses config: `config.rules.typ001.exempt_dunder`, `exempt_self_cls`

### Step 1.2: Write unit tests for TYP001
**File**: `tests/test_rules_typ001.py`

Test cases:
- Missing annotation on all params
- Partial annotations (only missing flagged)
- `self`/`cls` exempt
- Dunder methods exempt (if configured)
- Fully annotated = no diagnostics

### Step 1.3: Enable TYP001 scenario tests
**File**: `tests/linter_scenarios_tests.py`

Remove `@pytest.mark.skip` from TYP001 tests.

**Validation**:
```bash
pytest tests/test_rules_typ001.py tests/linter_scenarios_tests.py -k TYP001 -v
pytest --tb=short -q  # All tests pass
mypy src/
```

---

## Phase 2: TYP002 - Missing Return Annotations

### Step 2.1: Implement TYP002 detection
**File**: `src/pyguard/rules/typ002.py`

AST visitor that:
- Visits `FunctionDef` and `AsyncFunctionDef`
- Checks if `returns` is `None` (missing annotation)
- Exemptions: `__init__`, lambdas (can't annotate), `@override`

### Step 2.2: Implement TYP002 autofix (conservative)
**File**: `src/pyguard/rules/typ002.py`

Only add `-> None` when:
- No return statements with values
- Not a generator (no `yield`)
- Already missing annotation

### Step 2.3: Write unit tests and enable scenarios
**Files**: `tests/test_rules_typ002.py`, enable in `linter_scenarios_tests.py`, `fix_scenarios_tests.py`

**Validation**:
```bash
pytest -k TYP002 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 3: TYP003 - Missing Variable Annotations

### Step 3.1: Implement TYP003 detection
**File**: `src/pyguard/rules/typ003.py`

AST visitor that:
- Tracks scope (module, class, function)
- Flags `Name = value` assignments without annotation
- Respects `config.rules.typ003.scope` (module/class/local)
- Exemptions: `_`, for-loop targets, comprehension vars

### Step 3.2: Write unit tests and enable scenarios

**Validation**:
```bash
pytest -k TYP003 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 4: TYP010 - Legacy Typing Syntax

### Step 4.1: Implement TYP010 detection
**File**: `src/pyguard/rules/typ010.py`

Detect subscript annotations using legacy `typing` module:
- `Optional[T]` → suggest `T | None`
- `Union[A, B]` → suggest `A | B`
- `List[T]` → suggest `list[T]`
- `Dict[K, V]` → suggest `dict[K, V]`
- `Tuple`, `Set`, `FrozenSet`, `Type`

### Step 4.2: Implement TYP010 autofix (using LibCST)
**File**: `src/pyguard/fixers/typ010.py`

Using LibCST for robust AST-based rewriting:
- Replace legacy syntax with modern equivalents
- Handle nested types recursively
- Remove unused `typing` imports
- Preserve formatting/comments/whitespace exactly

**Dependency**: Add `libcst>=1.0` to `pyproject.toml` optional dependencies (`[dev]` or `[fix]`)

### Step 4.3: Write unit tests and enable scenarios

**Validation**:
```bash
pytest -k TYP010 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 5: KW001 - Keyword-Only Parameters

### Step 5.1: Implement KW001 detection
**File**: `src/pyguard/rules/kw001.py`

AST visitor that:
- Checks functions with `>= min_params` parameters
- Flags if no `*` separator in arguments
- Exemptions: dunder, private (`_func`), `@override`
- Uses config: `config.rules.kw001.min_params`, exemption flags

### Step 5.2: Implement KW001 autofix (unsafe, opt-in)
**File**: `src/pyguard/fixers/kw001.py`

Transform `def f(a, b, c):` → `def f(*, a, b, c):`
- Preserve `self`/`cls` before `*`
- Only with `--unsafe-fixes` flag

### Step 5.3: Write unit tests and enable scenarios

**Validation**:
```bash
pytest -k KW001 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 6: IMP001 - In-Function Imports

### Step 6.1: Implement IMP001 detection
**File**: `src/pyguard/rules/imp001.py`

AST visitor that:
- Tracks scope (module level vs function body)
- Flags `Import` and `ImportFrom` inside functions
- Exemptions: `TYPE_CHECKING` blocks, `try/except ImportError`

### Step 6.2: Implement IMP001 autofix (limited)
**File**: `src/pyguard/fixers/imp001.py`

Move imports to module level:
- Only simple imports (no conflicts)
- Preserve import ordering
- Skip conditional imports

### Step 6.3: Write unit tests and enable scenarios

**Validation**:
```bash
pytest -k IMP001 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 7: RET001 - Heterogeneous Tuple Returns

### Step 7.1: Implement RET001 detection
**File**: `src/pyguard/rules/ret001.py`

AST visitor that:
- Checks return type annotations for `tuple[T1, T2, T3]` (heterogeneous)
- Flags the return statement(s)
- Exemptions: `tuple[T, ...]` (homogeneous variadic)
- Suggest: "Use dataclass or NamedTuple"

### Step 7.2: Write unit tests and enable scenarios

**No autofix** — requires architectural rewrite.

**Validation**:
```bash
pytest -k RET001 -v
pytest --tb=short -q
mypy src/
```

---

## Phase 8: EXP001 & EXP002 - Export Rules

### Step 8.1: Implement EXP001 detection
**File**: `src/pyguard/rules/exp001.py`

Detect dataclasses/NamedTuples defined inside functions that are used as return types.

### Step 8.2: Implement EXP002 detection
**File**: `src/pyguard/rules/exp002.py`

Detect modules with public symbols but no `__all__`.

### Step 8.3: Write unit tests and enable scenarios

**Validation**:
```bash
pytest -k "EXP001 or EXP002" -v
pytest --tb=short -q
mypy src/
```

---

## Phase 9: Ignore Pragma System

### Step 9.1: Implement ignore comment parsing
**File**: `src/pyguard/ignores.py`

Parse comments:
- `# pyguard: ignore[TYP001]`
- `# pyguard: ignore[TYP001] because: legacy code`
- Block-level and file-level pragmas

### Step 9.2: Integrate with runner
**File**: `src/pyguard/runner.py`

Filter diagnostics based on:
- Line-level ignores
- Governance: `require_reason`, `disallow`, `max_per_file`

### Step 9.3: Write unit tests

**Validation**:
```bash
pytest tests/test_ignores.py -v
pytest --tb=short -q
mypy src/
```

---

## Validation Gates (Every Phase)

After each phase, run the full validation suite:

```bash
# Unit tests for the new rule
pytest tests/test_rules_<code>.py -v

# TDD scenario tests (unskipped for this rule)
pytest tests/linter_scenarios_tests.py -k <CODE> -v
pytest tests/fix_scenarios_tests.py -k <CODE> -v

# Full regression
pytest --tb=short -q

# Type checking
mypy src/

# Linting
ruff check src/

# Self-check (pyguard on pyguard)
python -m pyguard lint src/
```

---

## Summary Table

| Phase | Rule | Detection | Autofix | Complexity |
|-------|------|-----------|---------|------------|
| 0 | Framework | Setup | N/A | Low |
| 1 | TYP001 | Missing param annotations | No | Medium |
| 2 | TYP002 | Missing return annotations | `-> None` only | Medium |
| 3 | TYP003 | Missing var annotations | No | Medium |
| 4 | TYP010 | Legacy typing syntax | Full transform | High |
| 5 | KW001 | Non-keyword-only params | Unsafe opt-in | Medium |
| 6 | IMP001 | In-function imports | Limited | Medium |
| 7 | RET001 | Heterogeneous tuples | No | Medium |
| 8 | EXP001/2 | Export rules | No | Low |
| 9 | Ignores | Pragma system | N/A | Medium |

---

## File Structure After Implementation

```
src/pyguard/
├── rules/
│   ├── __init__.py      # Registry, get_enabled_rules()
│   ├── base.py          # Rule protocol
│   ├── typ001.py        # Missing param annotations
│   ├── typ002.py        # Missing return annotations
│   ├── typ003.py        # Missing var annotations
│   ├── typ010.py        # Legacy typing syntax
│   ├── kw001.py         # Keyword-only params
│   ├── imp001.py        # In-function imports
│   ├── ret001.py        # Heterogeneous tuples
│   ├── exp001.py        # Module-level return types
│   └── exp002.py        # __all__ enforcement
├── fixers/
│   ├── __init__.py
│   ├── typ002.py        # Add -> None
│   ├── typ010.py        # Modernize typing
│   ├── kw001.py         # Add * separator
│   └── imp001.py        # Move imports
├── ignores.py           # Pragma parsing
└── ... (existing modules)
```
