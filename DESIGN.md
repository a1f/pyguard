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
- **Interactive tryout mode** for reviewing fixes before applying

The first milestone is a usable CLI installable via pip, supporting single file and repository-wide execution, with deterministic output suitable for CI.

---

## 2. Non-Goals

- Replacing Black/Ruff/Flake8 wholesale. This tool complements them.
- Proving type correctness end-to-end (that remains the job of Pyright/MyPy).
- Fully automatic deep refactors (e.g., updating all call sites after signature changes).

---

## 3. Core UX and Product Shape

### 3.1 Modes

- **lint**: read-only, emits diagnostics with codes and locations.
- **fix**: safe, local transformations (syntax rewrites, easy edits). `--tryout` for interactive approval.
- **explain**: human-readable rule documentation and examples.

### 3.2 Output formats

- Human-readable console output
- `--format=json` for tool/agent integration
- `--diff` patch output for review workflows
- `--verbose`/`--debug` for troubleshooting

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
  - `pyguard lint` — detect issues
  - `pyguard fix` — apply safe fixes (`--diff`, `--tryout`, `--check`)
  - `pyguard explain` — rule documentation
  - `pyguard config` — show/validate configuration
- pip installable, with `console_scripts` entrypoint
- Pre-commit hook template provided

### 6.5 Agent integration boundary

JSON diagnostics output includes:

- rule code, message, file, range
- fix availability flag per diagnostic
- structured output suitable for CI and editor integrations

---

## 7. Current Status

**What PyGuard can do right now:**

- Install via `pip install -e .` and run as `pyguard` CLI
- `pyguard lint <paths>` — scans Python files, runs all 9 rules, reports diagnostics
- `pyguard config` — displays resolved configuration (text or `--json`)
- `pyguard config --validate` — validates `pyproject.toml` configuration
- All 9 lint rules implemented: TYP001, TYP002, TYP003, TYP010, KW001, IMP001, RET001, EXP001, EXP002
- 5 autofixers: TYP010 (LibCST), TYP002, TYP003, IMP001 (tokenize), KW001 (cross-file)
- Fix pipeline (`fixers/pipeline.py`) chains str-to-str fixers in dependency order
- Ignore pragma system with inline, block, and file-level suppression + governance (IGN001-003)
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
| `runner.py` | Lint orchestrator pipeline (scan → parse → check → ignore) |
| `ignores.py` | Ignore pragma parsing and diagnostic filtering |
| `rules/*.py` | 9 rule modules + base protocol + registry |
| `fixers/*.py` | 5 fixer modules + pipeline + shared utils |

**Test coverage:** 457 tests passing across 22 test files. mypy strict and ruff clean.

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

### Phase 2 — Ignore System + Rule Framework [DONE]

Ignore pragma system and rule framework with all 9 rules.

### Phase 3 — Typing Rules [DONE]

TYP001, TYP002, TYP003, TYP010 — detection + autofixers.

### Phase 4 — API & Return Rules [DONE]

KW001, RET001, EXP001, EXP002 — detection + KW001 autofix.

---

### Phase 5 — CLI Commands: fix + explain

Wire the existing fixers into CLI commands and add rule documentation.

#### Step 10 — `pyguard fix` command

Add a `fix` subcommand that applies safe autofixes to files.

```
pyguard fix src/              # fix files in-place
pyguard fix src/ --diff       # print unified diff, don't write
pyguard fix src/ --check      # exit 1 if any file would change (CI mode)
```

Implementation:
- Read files via scanner, run `fix_all()` pipeline (TYP010 → IMP001 → TYP002 → TYP003)
- Compare before/after: if changed, write back (or print diff in `--diff` mode)
- Report summary: `Fixed 3 files, 12 issues`
- `--check` mode for CI: exit 1 if any file would be modified, exit 0 if clean
- KW001 fixer excluded from pipeline (unsafe, cross-file) — separate `--unsafe-fixes` flag later

**Exit criteria:** `pyguard fix` modifies files correctly; `--diff` output is reviewable; `--check` works in CI.

#### Step 11 — `pyguard explain` command

Add an `explain` subcommand that prints human-readable rule documentation.

```
pyguard explain TYP001        # show rule explanation
pyguard explain --all         # list all rules with summaries
```

For each rule, display:
- Code and name
- What it detects and why it matters
- Good/bad code examples
- Available autofix (if any)
- Configuration options
- How to suppress (`# pyguard: ignore[CODE] because: ...`)

Implementation:
- Each rule module exposes a docstring or structured metadata
- `explain` command reads metadata and formats for terminal
- `--all` flag lists all rules in a table with code, severity, and one-line description

**Exit criteria:** every rule has a useful explanation; `--all` lists all 9 rules.

---

### Phase 6 — Logging + Tryout Mode

Add observability for debugging and an interactive fix preview workflow.

#### Step 12 — Structured logging

Add `--verbose` and `--debug` flags for troubleshooting.

```
pyguard lint src/ --verbose   # show files scanned, rules applied, timing
pyguard lint src/ --debug     # full trace: AST visits, ignore resolution, config
```

Implementation:
- Use Python `logging` module with named loggers per module (`pyguard.runner`, `pyguard.rules.typ001`, etc.)
- `--verbose` → INFO level: file count, rule count, timing per phase
- `--debug` → DEBUG level: per-file details, AST node visits, ignore pragma matches, config resolution
- Log to stderr so stdout remains clean for `--format json` piping
- Add timing instrumentation to runner phases (scan, parse, check, ignore, format)

**Exit criteria:** `--verbose` shows useful progress; `--debug` is sufficient to diagnose false positives/negatives.

#### Step 13 — Tryout mode (`pyguard fix --tryout`)

Interactive fix preview: show each proposed change, let user approve or skip.

```
pyguard fix src/ --tryout     # interactive: show diff per file, ask before writing
```

Workflow:
1. Run fix pipeline on each file
2. If file changed, display a colored unified diff
3. Prompt: `Apply this fix? [y]es / [n]o / [a]ll / [q]uit`
4. `y` — write this file, continue to next
5. `n` — skip this file, continue to next
6. `a` — apply all remaining without asking
7. `q` — stop, don't apply remaining files

This is the "suggest edits → user approves → apply" workflow. Combines `--diff` preview with interactive approval.

**Exit criteria:** tryout mode shows diffs, respects user choices, writes only approved files.

---

### Phase 7 — Packaging & Polish

Final polish for public release.

#### Step 14 — Packaging, Pre-commit, CI
- Publishable packaging metadata, versioning, changelog
- Pre-commit hook configuration (`.pre-commit-hooks.yaml`)
- CI example (GitHub Actions) with recommended pipeline order
- README with usage, configuration reference, rule catalog

**Exit criteria:** drop-in adoption; reproducible install; stable CLI.

---

## 9. Key Decisions Recorded

1. **Fix technology**: LibCST for complex transforms (TYP010), tokenize for simple insertions (TYP002, TYP003, IMP001, KW001)
2. **Typing enforcement scope**: all scopes by default (module, class, local)
3. **Keyword-only enforcement scope**: public API only (exempt dunder, private, overrides)
4. **Rewrite policy**: dropped — no automatic rewrite-assist mode. Complex refactors are left to the user/agent
5. **Export policy**: EXP001 enforces module-level return types; EXP002 enforces `__all__`
6. **GitHub formatter**: dropped — `text` and `json` formats are sufficient; CI integration via `--format json`

---

## 10. Repository Structure

```
src/pyguard/
├── __init__.py
├── __main__.py
├── cli.py              # Click CLI (lint, config commands)
├── config.py           # Config loading from pyproject.toml
├── constants.py        # Rule codes, enums, defaults
├── types.py            # Dataclasses for configuration
├── scanner.py          # File discovery with include/exclude globs
├── parser.py           # AST parsing with syntax error capture
├── diagnostics.py      # Diagnostic data model
├── formatters.py       # Text and JSON output formatters
├── runner.py           # Lint orchestrator pipeline
├── ignores.py          # Ignore pragma parsing and filtering
├── rules/
│   ├── __init__.py
│   ├── base.py         # Rule protocol
│   ├── registry.py     # Rule registry, get_enabled_rules()
│   ├── typ001.py       # Missing parameter annotations
│   ├── typ002.py       # Missing return annotations
│   ├── typ003.py       # Missing variable annotations
│   ├── typ010.py       # Legacy typing syntax
│   ├── kw001.py        # Keyword-only parameters
│   ├── ret001.py       # Heterogeneous tuple returns
│   ├── imp001.py       # In-function imports
│   ├── exp001.py       # Module-level return types
│   └── exp002.py       # __all__ enforcement
└── fixers/
    ├── __init__.py
    ├── _util.py        # Shared fixer utils (parse, tokenize, validate)
    ├── pipeline.py     # fix_all() — chains fixers in dependency order
    ├── typ002.py       # Add -> None (tokenize-based)
    ├── typ003.py       # Add variable annotations (tokenize-based)
    ├── typ010.py       # Modernize typing syntax (LibCST-based)
    ├── kw001.py        # Insert * separator (tokenize, cross-file)
    └── imp001.py       # Move imports to module level (tokenize-based)
```

---

## 11. Definition of Done (for v0.1)

- [x] Lint mode supports all 9 rules (TYP001-TYP010, KW001, IMP001, RET001, EXP001-002)
- [x] Fixers implemented: TYP010, TYP002, TYP003, IMP001, KW001
- [x] Fix pipeline chains fixers in dependency order
- [x] Ignore pragmas with governance (require_reason, disallow, max_per_file)
- [x] Config via `pyproject.toml`
- [x] Deterministic output + JSON output
- [x] pip installable with `pyguard` CLI
- [x] 457 tests, mypy strict, ruff clean
- [ ] `pyguard fix` CLI command (Phase 5)
- [ ] `pyguard explain` CLI command (Phase 5)
- [ ] Logging with `--verbose`/`--debug` (Phase 6)
- [ ] Tryout mode `--tryout` (Phase 6)
- [ ] Packaging, pre-commit, CI (Phase 7)

---

## 12. Integration Test Projects

Real-world Python code for smoke-testing PyGuard against untyped/legacy-typed codebases:

| Project | Description | What it exercises |
|---------|-------------|-------------------|
| [suurjaak/pyscripts](https://github.com/suurjaak/pyscripts) | 9 small utility scripts (CC0). No types at all, ~100-350 lines each. `db.py` has 18 methods, `duplicates.py` has 6 functions. | TYP001, TYP002, TYP003, KW001, EXP002 |
| [cdeil/python-cli-examples](https://github.com/cdeil/python-cli-examples) | CLI examples using argparse/click/cliff. Small demo scripts. | TYP001, TYP002, IMP001 |
| [johnthagen/python-blueprint](https://github.com/johnthagen/python-blueprint) | Best-practices Python project template. Modern but uses legacy typing in some places. | TYP010, EXP002 |
| Self-lint (`pyguard lint src/`) | Run PyGuard on its own codebase. Should produce zero diagnostics. | All rules — regression test |
