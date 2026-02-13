# PyGuard - Project Instructions for Claude

## Overview

PyGuard is a strict Python linter enforcing typing, keyword-only APIs, and structured returns. It reads configuration from `pyproject.toml` and provides CLI commands for linting Python files.

## Tech Stack

- **Python**: 3.11+ (uses `tomllib` from stdlib)
- **CLI**: Click
- **Config**: `pyproject.toml` with `[tool.pyguard]` section
- **Testing**: pytest, pytest-cov
- **Type Checking**: mypy (strict mode)
- **Linting**: ruff
- **CST Rewriting**: libcst (optional `[fix]` dependency, used by TYP010 fixer)

## Project Structure

```
pyguard/
├── pyproject.toml          # Project metadata + [tool.pyguard] schema
├── DESIGN.md               # Full design document
├── plans/                  # Implementation plans
│   └── linting-rules-implementation.md
├── src/
│   └── pyguard/
│       ├── __init__.py     # Empty (package marker only)
│       ├── __main__.py     # Enable `python -m pyguard`
│       ├── cli.py          # CLI entry point (click)
│       ├── config.py       # Config loading logic
│       ├── constants.py    # Rule codes, default values, enums
│       ├── types.py        # Common types and dataclasses
│       ├── diagnostics.py  # Diagnostic data model
│       ├── parser.py       # AST parsing with syntax error detection
│       ├── scanner.py      # File discovery (glob patterns)
│       ├── runner.py       # Lint runner (scan → parse → check pipeline)
│       ├── formatters.py   # Text and JSON output formatters
│       ├── rules/
│       │   ├── __init__.py # Empty
│       │   ├── base.py     # Rule protocol (structural interface)
│       │   ├── registry.py # Rule registry, get_enabled_rules()
│       │   ├── typ001.py   # Missing parameter annotations
│       │   ├── typ002.py   # Missing return annotations
│       │   ├── typ003.py   # Missing variable annotations
│       │   └── typ010.py   # Legacy typing syntax detection
│       └── fixers/
│           ├── __init__.py # Empty
│           ├── _util.py    # Shared fixer utils (parse, tokenize, validate)
│           ├── typ002.py   # Add -> None (tokenize-based)
│           ├── typ003.py   # Add variable annotations (tokenize-based)
│           └── typ010.py   # Modernize typing syntax (LibCST-based)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── linter_scenarios_tests.py   # TDD scenarios for all rules
│   ├── fix_scenarios_tests.py      # TDD scenarios for all fixers
│   ├── test_rules_framework.py     # Rule protocol and registry tests
│   ├── test_rules_typ001.py        # TYP001 unit tests
│   ├── test_rules_typ002.py        # TYP002 unit tests
│   ├── test_rules_typ010.py        # TYP010 unit tests
│   ├── test_runner.py              # Runner pipeline tests
│   ├── test_parser.py              # Parser tests
│   ├── test_scanner.py             # File scanner tests
│   ├── test_diagnostics.py         # Diagnostic model tests
│   ├── test_formatters.py          # Formatter tests
│   ├── test_config.py              # Config system tests
│   └── test_cli.py                 # CLI integration tests
└── README.md
```

## Environment

Always use the project venv Python:

```bash
.venv/bin/python
```

## Development Setup

```bash
# Install in development mode with dev dependencies
.venv/bin/python -m pip install -e ".[dev]"

# Verify installation
.venv/bin/python -m pyguard --help
```

## Common Commands

```bash
# Run linter
.venv/bin/python -m pyguard lint src/

# Run tests
.venv/bin/python -m pytest --tb=short -q

# Type checking
.venv/bin/python -m mypy src/ --strict

# Lint the codebase
.venv/bin/python -m ruff check src/

# Validation gate (run after every step before committing)
.venv/bin/python -m pytest --tb=short -q && .venv/bin/python -m mypy src/ --strict && .venv/bin/python -m ruff check src/
```

## Code Conventions

### Type Annotations
- All function parameters and return types must be annotated
- Use `from __future__ import annotations` at the top of every module
- Use modern typing syntax (e.g., `list[str]` not `List[str]`, `X | None` not `Optional[X]`)

### Dataclasses
- Use `@dataclass(frozen=True, slots=True)` for immutability and memory efficiency
- Configuration objects should be immutable

### Imports
- Use `TYPE_CHECKING` blocks for import-only-for-types to avoid circular imports
- Group imports: stdlib, third-party, local

### Error Handling
- Use `ConfigError` for configuration-related errors
- Collect all validation errors before raising (better UX than fail-fast)

## Rule Implementation Status

| Code | Description | Detection | Autofix | Status |
|------|-------------|-----------|---------|--------|
| TYP001 | Missing parameter annotations | AST visitor | No | Done |
| TYP002 | Missing return annotations | AST visitor | `-> None` (tokenize) | Done |
| TYP003 | Missing variable annotations | AST visitor | Infer type (tokenize) | Done |
| TYP010 | Legacy typing syntax | AST visitor | Full transform (LibCST) | Done |
| KW001 | Keyword-only parameters | — | — | Pending |
| RET001 | Heterogeneous tuple returns | — | — | Pending |
| IMP001 | In-function imports | — | — | Pending |
| EXP001 | Module-level return types | — | — | Pending |
| EXP002 | `__all__` enforcement | — | — | Pending |

## Adding a New Rule

1. Create `src/pyguard/rules/<code>.py` — class with `code` property + `check()` method + `_Visitor(ast.NodeVisitor)`
2. Register in `src/pyguard/rules/registry.py` — import rule class + add to `_all_rules()` list
3. Create `src/pyguard/fixers/<code>.py` (if autofix applies) — tokenize-based for simple insertions, LibCST for complex transforms
4. Create `tests/test_rules_<code>.py` — follow pattern from `test_rules_typ001.py`
5. Enable scenarios in `tests/linter_scenarios_tests.py` — remove `@pytest.mark.skip`, add rule to `_check_code` dict, replace `assert False` stubs with `_check_code`/`_assert_diagnostics_match` calls
6. Enable fix scenarios in `tests/fix_scenarios_tests.py` — remove `@pytest.mark.skip`, import fixer function, replace `assert False` stubs with actual fixer calls

### Rule Architecture

- **Protocol**: `Rule` in `rules/base.py` — requires `code` property and `check()` method
- **Registry**: `rules/registry.py` — `get_enabled_rules(config=...)` returns non-OFF rules
- **Runner**: `runner.py` — iterates enabled rules over parsed files, collects diagnostics
- **Config**: Rule severity via `config.get_severity("CODE")`, rule-specific options via `config.rules.<code>`
- **Fixer utils**: `fixers/_util.py` — `parse_source()`, `tokenize_source()`, `apply_insertions()` with output validation

### LibCST Notes

- `libcst.Module` has no `.walk()` method — use `.visit()` with a `CSTTransformer` subclass
- For read-only collection, subclass `CSTTransformer` and override `visit_*` methods (return `True` to continue)
- `RemovalSentinel.REMOVE` removes statements but may leave leading blank lines — strip with `.lstrip("\n")`

## Configuration Schema

PyGuard is configured via `[tool.pyguard]` in `pyproject.toml`:

```toml
[tool.pyguard]
python_version = "3.11"
include = ["src/**/*.py", "tests/**/*.py"]
exclude = ["**/__pycache__/**"]
output_format = "text"  # "text" | "json" | "github"
show_source = true
color = "auto"  # "auto" | "always" | "never"

[tool.pyguard.rules]
TYP001 = "error"   # "error" | "warn" | "off"
KW001 = "warn"

[tool.pyguard.rules.KW001]
min_params = 2
exempt_dunder = true

[tool.pyguard.ignores]
require_reason = true
disallow = []
max_per_file = null
```

## Testing

- Tests are in `tests/` directory
- Use pytest fixtures from `conftest.py`
- Test both success cases and error cases
- CLI tests use Click's `CliRunner`
- Scenario tests (`linter_scenarios_tests.py`, `fix_scenarios_tests.py`) are TDD-style with `@pytest.mark.skip` for unimplemented rules
- Unit tests per rule: `test_rules_<code>.py` with `_make_parse_result()` helper

## Key Design Decisions

1. **Click for CLI** - Better UX, composable commands
2. **Dataclasses for config** - Minimal dependencies, immutable by default
3. **pyproject.toml only** - Consistent with modern Python tooling (ruff, black, mypy)
4. **Strict defaults** - Encourage best practices for typing rules
5. **LibCST for complex fixers** - Preserves formatting, handles nested transforms (optional dependency)
6. **Tokenize for simple fixers** - No extra dependency for insertion-only fixes (-> None, `: type`)

---

## Development Workflow

### Planning Structure

All work must follow a structured plan with three levels:
- **Chapters** - Major feature areas or milestones
- **Phases** - Groups of related steps within a chapter
- **Steps** - Minimal implementation units (the atomic work item)

See `plans/linting-rules-implementation.md` for the current implementation plan.

### Commit Rules

1. **One step = one commit** - Each step is a minimal unit of implementation
2. **Size limit** - Commits should be 100-200 lines of code (excluding tests)
3. **Maximum** - Never exceed 300 lines per commit (excluding tests)
4. **No AI attribution** - Never include "Co-Authored-By: Claude" or similar in commit messages
5. **Descriptive messages** - Commit messages should describe what changed and why

### Implementation Workflow

When implementing a step, follow this sequence:

1. **Plan** - Use `coder` agent with `/python-coding-rules` skill
2. **Implement** - Write code following the plan
3. **Plan Tests** - Use `test-suite-architect` agent to design test scenarios
4. **Implement Tests** - Use `coder` agent to write the planned tests
5. **Review** - Use `code-reviewer` agent to review the code
6. **Security Review** - Use `security-auditor` agent to check for vulnerabilities
7. **Fix Issues** - If reviewers find improvements, send back to `coder` agent
8. **Repeat** - Continue until no improvements needed
9. **Commit** - Create commit with descriptive message

### Testing Requirements

- **Use mocks and fakes** - All tests must use mock/fake data, never real external resources
- **Isolation** - Tests should be independent and not rely on external state
- **Fixtures** - Use pytest fixtures for common test setup
- **Coverage** - Aim for high coverage of edge cases and error paths

### Agent Usage

| Agent | Purpose |
|-------|---------|
| `coder` | Implement code changes (use with `/python-coding-rules` skill) |
| `test-suite-architect` | Plan test scenarios before implementation |
| `code-reviewer` | Review structure, style, naming, typos |
| `security-auditor` | Find security vulnerabilities |
| `bug-hunter` | Find logic errors, edge cases, bugs |

### Single Step Execution

**Important**: Implement ONE step at a time unless explicitly asked otherwise. This ensures:
- Small, reviewable changes
- Easy rollback if issues arise
- Clear progress tracking
- Manageable commit sizes
