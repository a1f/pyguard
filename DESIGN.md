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

## 7. Current Status

**What PyGuard can do right now:**

- Install via `pip install -e .` and run as `pyguard` CLI
- `pyguard lint <paths>` — scans Python files, detects syntax errors (SYN001), reports with exit code 1
- `pyguard config` — displays resolved configuration (text or `--json`)
- `pyguard config --validate` — validates `pyproject.toml` configuration
- File discovery with glob-based include/exclude patterns from `[tool.pyguard]`
- Config loading from `pyproject.toml` with per-rule severity, ignore governance, and rule-specific options
- Text and JSON output formatters with source line display and caret positioning
- Deterministic, sorted diagnostic output suitable for CI

**Modules implemented:**

| Module | Purpose |
|--------|---------|
| `cli.py` | Click CLI with `lint` and `config` commands |
| `config.py` | Config loading and validation from `pyproject.toml` |
| `constants.py` | Rule codes, enums, defaults |
| `types.py` | Dataclasses for configuration |
| `scanner.py` | File discovery with include/exclude globs |
| `parser.py` | AST parsing with syntax error capture |
| `diagnostics.py` | `Diagnostic`, `SourceLocation`, `DiagnosticCollection` |
| `formatters.py` | Text and JSON formatters, summary |
| `runner.py` | Lint orchestrator pipeline |

**Test coverage:** 101 tests passing across 7 test files. mypy and ruff clean.

---

## 8. Implementation Plan

### Phase 1 — Foundation [DONE]

Everything needed for a working CLI that can scan files and report syntax errors.

#### Step 0 — Repository Bootstrap [DONE]
- Initialize repo structure: `src/pyguard/`, `tests/`, `pyproject.toml`
- Baseline tooling: ruff, mypy for the linter's own codebase
- `console_scripts` entrypoint

#### Step 1 — Configuration System [DONE]
- Config schema in `pyproject.toml` under `[tool.pyguard]`
- Config loading, validation, defaults
- Include/exclude glob patterns, per-rule severity, ignore governance options
- `pyguard config` and `pyguard config --validate` commands

#### Step 2 — Parser + File Walker + Diagnostic Model [DONE]
- File discovery (`scanner.py`) respecting include/exclude
- AST parsing (`parser.py`) with syntax error detection
- Diagnostic data model (`diagnostics.py`)
- Text and JSON output formatters (`formatters.py`)
- Lint orchestrator (`runner.py`) wiring scan-parse-collect-format pipeline
- `pyguard lint` command with `--format`, `--color`, `--show-source` overrides

---

### Phase 2 — Ignore System + Rule Framework

Build the infrastructure for suppressing diagnostics and plugging in lint rules.

#### Step 3 — Ignore/Skip Pragmas
- Create `src/pyguard/ignores.py`
- Parse `# pyguard: ignore[CODE] because: ...` comments (line-level)
- Parse `# pyguard: ignore-file[CODE] because: ...` comments (file-level)
- Block/function-level ignore (comment preceding definition)
- Enforce governance: `require_reason`, `disallow`, `max_per_file`
- Filter diagnostics through ignore system in runner
- Tests: suppression accuracy, governance violations, edge cases

**Exit criteria:** ignores suppress diagnostics exactly as specified; governance flags violations.

#### Step 4 — Rule Framework + First Rule (IMP001)
- Create `src/pyguard/rules/base.py` — rule interface (`check()` method, rule metadata)
- Create rule registry with discovery from `rules/` package
- Integrate rule execution into runner pipeline (parse → check rules → collect diagnostics)
- Create `src/pyguard/rules/imp001.py` — detect imports inside function bodies
- Handle edge cases: `TYPE_CHECKING` blocks, `try/except ImportError` patterns
- Tests: valid/invalid import positions, exemptions, integration with ignore system

**Exit criteria:** IMP001 works reliably; suppression works; unit tests pass.

---

### Phase 3 — Typing Rules

Core value proposition: enforce type annotations across the codebase.

#### Step 5 — Function Annotation Rules (TYP001 + TYP002)
- Create `src/pyguard/rules/typ001.py` — missing parameter annotations
- Create `src/pyguard/rules/typ002.py` — missing return annotations
- Configurable exemptions: dunder methods (`exempt_dunder`), `self`/`cls` params (`exempt_self_cls`)
- Override detection heuristic: `@override` decorator, protocol implementations
- Tests: functions, methods, lambdas, nested functions, decorators, exemptions

**Exit criteria:** correct detection; good error messaging; exemptions work.

#### Step 6 — Modern Typing Syntax (TYP010)
- Create `src/pyguard/rules/typ010.py` — detect legacy typing imports and usage
- Detect: `Optional[T]`, `Union[A, B]`, `List[T]`, `Dict[K, V]`, `Tuple[...]`, `Set[T]`, `FrozenSet[T]`, `Type[T]`
- Respect `python_version` config (only flag if target version supports modern syntax)
- Tests: all legacy forms, nested generics, `from typing import ...` vs `typing.List`

**Exit criteria:** deterministic detection; tests cover edge cases.

#### Step 7 — Variable Annotation Rule (TYP003)
- Create `src/pyguard/rules/typ003.py` — missing variable annotations
- Configurable scope: `module`, `class`, `local` (default: module-only)
- Exemptions: `_ = ...`, comprehension targets, for-loop targets, augmented assignments
- Tests: all scope levels, exemption cases, false positive avoidance

**Exit criteria:** module-level enforcement works with low false-positive rate.

---

### Phase 4 — API & Return Rules

Enforce API design patterns: keyword-only parameters, structured returns.

#### Step 8 — Keyword-Only API Rule (KW001)
- Create `src/pyguard/rules/kw001.py` — require `*` separator for keyword-only params
- Apply to public functions by default (non-underscore prefix)
- Configurable: `min_params` threshold, `exempt_dunder`, `exempt_private`, `exempt_overrides`
- Tests: various function signatures, methods, static/class methods, exemptions

**Exit criteria:** accurate detection; does not flag internal helpers; clear guidance.

#### Step 9 — Structured Return Rule (RET001)
- Create `src/pyguard/rules/ret001.py` — detect heterogeneous tuple returns
- Allow homogeneous variadic returns annotated as `tuple[T, ...]`
- Flag `return a, b` without structured type
- Produce diagnostic with suggestion (dataclass/NamedTuple)
- Tests: tuple returns, single returns, annotated returns, nested functions

**Exit criteria:** detection works; suggestions are usable; suppression works.

---

### Phase 5 — Fix Engine + Agent Integration

Add autofix capabilities and structured output for agent workflows.

#### Step 10 — Fix Infrastructure
- Choose fix technology (LibCST vs ast+tokenize)
- Create `src/pyguard/fixer.py` — fix engine with edit application
- Add `pyguard fix` CLI command
- Implement safe fixes: TYP010 rewrites (`Optional[T]` → `T | None`, etc.)
- Implement conservative fix: add `-> None` for functions without return statements
- `--diff` output mode for review workflows
- Tests: round-trip stability, formatting preservation, fix accuracy

**Exit criteria:** safe fixes apply correctly; `--diff` output is reviewable.

#### Step 11 — Rewrite Assist + Agent Boundary
- Define stable JSON schema for "rewrite-required diagnostics"
- `pyguard explain CODE` — human-readable rule explanation
- Structured rewrite plan payload in JSON output (suggested type name, fields, impacted locations)
- Optional: `pyguard rewrite --apply` gated behind explicit flag
- Tests: JSON schema validation, explain output, plan generation

**Exit criteria:** the tool can hand off complex cases to an agent workflow cleanly.

---

### Phase 6 — Packaging & Polish

Final polish for public release.

#### Step 12 — GithubFormatter + Output Polish
- Implement `GithubFormatter` class (`::error file=...,line=...,col=...::` format)
- Add `--format github` to CLI choices
- Tests: GitHub annotation format, multi-diagnostic output

#### Step 13 — Packaging, Pre-commit, CI
- Publishable packaging metadata, versioning, changelog
- Pre-commit hook configuration (`.pre-commit-hooks.yaml`)
- CI example (GitHub Actions) with recommended pipeline order
- README with usage, configuration reference, rule catalog

**Exit criteria:** drop-in adoption; reproducible install; stable CLI.

---

## 9. Key Decisions to Record Early

1. **Fix technology**: LibCST vs ad-hoc token edits
2. **Typing enforcement scope**: module-only vs locals by default
3. **Keyword-only enforcement scope**: public API only vs all functions
4. **Rewrite policy**: whether rewrite mode ever modifies call sites automatically
5. **Export policy**: whether to mandate `__all__` / re-exports for return types

---

## 10. Repository Structure

```
src/pyguard/
├── __init__.py
├── __main__.py
├── cli.py
├── config.py
├── constants.py
├── types.py
├── scanner.py
├── parser.py
├── diagnostics.py
├── formatters.py
├── runner.py
├── ignores.py          (Phase 2)
└── rules/              (Phase 2+)
    ├── __init__.py
    ├── base.py
    ├── imp001.py
    ├── typ001.py
    ├── typ002.py
    ├── typ003.py
    ├── typ010.py
    ├── kw001.py
    └── ret001.py

tests/
├── conftest.py
├── test_cli.py
├── test_config.py
├── test_diagnostics.py
├── test_scanner.py
├── test_parser.py
├── test_formatters.py
└── test_runner.py
```

---

## 11. Definition of Done (for v0.1)

- [ ] Lint mode supports: IMP001, TYP001, TYP002, TYP010
- [ ] Fix mode supports: TYP010 and trivial `-> None` insertions
- [ ] Ignore pragmas implemented with governance settings
- [x] Config via `pyproject.toml`
- [x] Deterministic output + JSON output
- [x] pip installable with `pyguard` CLI
- [ ] Basic docs + pre-commit example
