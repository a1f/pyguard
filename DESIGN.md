# Design Document: Strict Python Style Linter + Formatter (Agent Navigation Plan)

## 1. Purpose and Scope

Build a Python 3.11+ linter and formatter that enforces a strict style guide centered on:

- **Mandatory typing** (functions and variables)
- **Keyword-only APIs**
- **Structured returns** (no heterogeneous tuple packing)
- **Top-level imports only**
- **Modern typing syntax** (PEP 585 / PEP 604)
- **Configurable rules**, messages, and fix behavior
- **Explicit skip/ignore mechanisms**
- **Optional "rewrite assist" channel** for complex refactors

The first milestone is a usable CLI installable via pip, supporting single file and repository-wide execution, with deterministic output suitable for CI.

---

## 2. Non-Goals

- Replacing Black/Ruff/Flake8 wholesale. This tool complements them.
- Proving type correctness end-to-end (that remains the job of Pyright/MyPy).
- Fully automatic deep refactors by default (e.g., updating all call sites after signature changes). Those are "rewrite assist" only.

---

## 3. Core UX and Product Shape

### 3.1 Modes

- **lint**: read-only, emits diagnostics with codes and locations.
- **fix**: safe, local transformations (syntax rewrites, easy edits).
- **rewrite** (optional / gated): larger refactors (e.g., tuple → dataclass + update returns), potentially requiring human/agent involvement.

### 3.2 Output formats

- Human-readable console output
- `--format=json` for tool/agent integration
- `--diff` patch output for review workflows

### 3.3 Repository configuration

- `pyproject.toml` as the primary config surface
- Per-rule severity (`error`/`warn`/`off`)
- Allow/deny ignores, require ignore reason, ignore budgets

---

## 4. Style Rules (Initial Rule Set)

Each rule has:

- **Code** (stable identifier)
- **Category**
- **Rationale**
- **Lint behavior**
- **Fix behavior** (none/safe/unsafe/rewrite)
- **Ignore support**

### 4.1 Typing

| Code | Description |
|------|-------------|
| TYP001 | Missing function parameter annotations |
| TYP002 | Missing function return annotation |
| TYP003 | Missing variable annotation (configurable scope: module-level only vs all assignments) |
| TYP010 | Disallow legacy typing syntax (`Optional`, `List`, `Dict`, `Tuple`, etc. when 3.11+) |

**Fix**: `Optional[T]` → `T | None`, `List[T]` → `list[T]`, etc.

### 4.2 API clarity

| Code | Description |
|------|-------------|
| KW001 | Require keyword-only parameters (enforce `*`) for non-trivial functions |

Configurable exemptions: dunder methods, overrides, protocol implementations, small internal helpers

### 4.3 Return structure

| Code | Description |
|------|-------------|
| RET001 | Disallow heterogeneous tuple returns (`return a, b`) unless homogeneous variadic (e.g., `tuple[str, ...]`) |

Preferred: `@dataclass(frozen=True, slots=True)` or `NamedTuple`

**Fix**: generally rewrite-assisted

### 4.4 Imports

| Code | Description |
|------|-------------|
| IMP001 | Disallow imports inside function bodies |

**Fix**: safe only in simple cases; otherwise lint + recommend suppression with reason

### 4.5 Exports and discoverability (optional but recommended)

| Code | Description |
|------|-------------|
| EXP001 | Structured return types must be module-level and importable |
| EXP002 | Enforce `__all__` or explicit re-export policy (configurable) |

---

## 5. Ignore / Skip System

Provide three layers:

- **line**: `# pyguard: ignore[CODE1,CODE2] because: …`
- **block/function**: `# pyguard: ignore[CODE] because: …` immediately preceding definition
- **file**: `# pyguard: ignore-file[CODE] because: …` at top of file

Configurable governance:

```toml
require_ignore_reason = true
disallow_ignores = ["TYP002"]
max_ignores_per_file = N
```

---

## 6. Architecture Overview

### 6.1 Parsing and analysis

- Parse source with Python's AST (3.11 grammar)
- Track locations, scopes, and symbol tables minimally (enough for rule checks)
- Use `tokenize` / CST library optionally for formatting-preserving fixes (see decision below)

### 6.2 Fix engine

Two categories:

- **Text-safe fixes**: simple, local edits
- **CST-aware fixes**: preserve formatting and comments reliably

**Decision point early:**

Choose either:
- **LibCST** for robust codemods (recommended for fix/rewrite quality)
- or **ast + tokenize** for minimal dependencies (faster, but brittle for edits)

### 6.3 Rule framework

Rules implemented as independent modules with a shared interface:

```python
check(context) -> diagnostics[]
fix(diagnostic, context) -> edits[] | None
```

Rule registry loaded from entry points to support plugins later.

### 6.4 CLI and packaging

- `pyguard` CLI:
  - `pyguard lint`
  - `pyguard fix`
  - `pyguard rewrite`
- pip installable, with `console_scripts` entrypoint
- Pre-commit hook template provided

### 6.5 Agent integration boundary

JSON diagnostics output includes:

- rule code, message, file, range
- suggested rewrite plan (if available)
- "rewrite required" flag for non-autofixable issues

---

## 7. High-Level Implementation Steps (Navigation Plan)

This is the sequence the agent should follow when building from an empty repository. Each step results in a shippable increment.

### Step 0 — Repository Bootstrap

- Initialize repo structure: `src/pyguard/`, `tests/`, `pyproject.toml`
- Choose baseline tooling: ruff/black/mypy for the linter's own codebase
- Establish CI skeleton (lint, unit tests)

**Exit criteria**: `pip install -e .` works, `pyguard --help` prints.

---

### Step 1 — Configuration System

- Define config schema (pyproject)
- Implement config loading + validation + defaults
- Support ignore patterns (glob), excluded directories

**Exit criteria**: `pyguard lint` reads config and prints resolved settings.

---

### Step 2 — Parser + File Walker + Diagnostic Model

- Implement file discovery (all `.py` files; respect excludes)
- Parse AST per file; collect syntax errors
- Define diagnostic structure (code, message, severity, location)
- Implement JSON and text output formatting

**Exit criteria**: `pyguard lint path/` produces deterministic diagnostics for syntax errors and a placeholder rule.

---

### Step 3 — Ignore/Skip Pragmas

- Implement comment scanning and suppression logic
- Support line/block/file ignore variants
- Enforce ignore governance options (require reasons, disallowed codes)

**Exit criteria**: ignores suppress diagnostics exactly as specified; governance flags violations.

---

### Step 4 — Rule Framework + First Rule (Imports)

- Build rule interface, registry, and execution engine
- Implement IMP001 (no in-function imports)
- Add tests with fixtures for allowed/disallowed cases

**Exit criteria**: IMP001 works reliably; suppression works; unit tests pass.

---

### Step 5 — Typing Rules (Function-level First)

- Implement TYP001/TYP002 (params + return annotation)
- Add exemptions:
  - dunder methods (configurable)
  - overrides (heuristic: `@override`, base class method exists, Protocol implementations—configurable)
- Add basic safe autofix:
  - add `-> None` where function has no return statements (conservative)
  - otherwise lint only

**Exit criteria**: correct detection; conservative fix for trivial `-> None`; good error messaging.

---

### Step 6 — Modern Typing Syntax Upgrades

- Implement TYP010 "modernize typing syntax"
- Safe autofix:
  - `Optional[T]` → `T | None`
  - `Union[A,B]` → `A | B`
  - `List[T]` → `list[T]`, etc.
- Respect minimum Python version config

**Exit criteria**: deterministic rewrites; round-trip formatting stable after Black; tests cover edge cases.

---

### Step 7 — Variable Annotation Rule (Scoped Rollout)

- Implement TYP003 with config:
  - `scope = ["module", "class", "local"]` (start with module-only default)
- Avoid noisy false positives:
  - allow `_ = ...`
  - allow comprehensions targets
  - allow for-loop targets
- No autofix by default (or very conservative autofix only for empty containers as optional)

**Exit criteria**: module-level enforcement works with low false-positive rate.

---

### Step 8 — Keyword-Only API Rule

- Implement KW001:
  - policy-based: apply to public functions by default (non-underscore)
  - configurable exemptions: small arity, datamodel methods, callbacks
- Fix behavior:
  - lint-only by default (because call sites may break)
  - optional "rewrite assist" mode can propose patching call sites within repo

**Exit criteria**: accurate detection; does not spam internal/private helpers; clear remediation guidance.

---

### Step 9 — Structured Return Rule (Tuple Packing)

- Implement RET001:
  - detect tuple literal returns `return a, b`
  - allow homogeneous variadic returns when annotated as `tuple[T, ...]`
  - flag heterogeneous tuples and missing schema
- No safe autofix; produce a "rewrite plan" payload in JSON:
  - suggest dataclass/NamedTuple name
  - suggest fields inferred from local variable names (best-effort)
  - list impacted return statements

**Exit criteria**: detection works; suggestions are usable; suppression works.

---

### Step 10 — "Rewrite Assist" Integration (Agent Hook Boundary)

- Define a stable JSON schema for "rewrite-required diagnostics"
- Provide a helper command:
  - `pyguard explain CODE` (human explanation)
  - `pyguard plan` (emit structured rewrite plan)
- Optional: `pyguard rewrite --apply` gated behind explicit flag

**Exit criteria**: the tool can hand off complex cases cleanly to an agent workflow without mixing concerns.

---

### Step 11 — Packaging, Pre-commit, and CI Reference Integration

- Publishable packaging metadata, versioning, changelog
- Pre-commit hook example
- CI example (GitHub Actions) with recommended pipeline order:
  1. `pyguard fix` (optional)
  2. `black`
  3. `pyguard lint`
  4. `ruff`
  5. `pyright`/`mypy`

**Exit criteria**: "drop-in" adoption docs; reproducible install; stable CLI.

---

## 8. Key Decisions to Record Early

1. **Fix technology**: LibCST vs ad-hoc token edits
2. **Typing enforcement scope**: module-only vs locals by default
3. **Keyword-only enforcement scope**: public API only vs all functions
4. **Rewrite policy**: whether rewrite mode ever modifies call sites automatically
5. **Export policy**: whether to mandate `__all__` / re-exports for return types

---

## 9. Repository Skeleton (Proposed)

```
src/pyguard/
├── cli.py
├── config.py
├── runner.py
├── diagnostics.py
├── ignores.py
└── rules/
    ├── base.py
    ├── imp001_no_local_imports.py
    ├── typ001_annotations.py
    ├── typ010_modern_typing.py
    ├── kw001_keyword_only.py
    └── ret001_no_tuple_packing.py

tests/
└── fixtures/
    └── (rule-specific tests)
```

---

## 10. Definition of Done (for v0.1)

- [ ] Lint mode supports: IMP001, TYP001, TYP002, TYP010
- [ ] Fix mode supports: TYP010 and trivial `-> None` insertions
- [ ] Ignore pragmas implemented with governance settings
- [ ] Config via `pyproject.toml`
- [ ] Deterministic output + JSON output
- [ ] pip installable with `pyguard` CLI
- [ ] Basic docs + pre-commit example

---

## Next Steps

If you create the empty repository now, the best immediate next action is **Step 0 + Step 1** (bootstrap + config), because they unblock everything else and give you a stable command surface for iterative rule implementation.
