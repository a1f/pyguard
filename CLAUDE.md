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

## Project Structure

```
pyguard/
├── pyproject.toml          # Project metadata + [tool.pyguard] schema
├── src/
│   └── pyguard/
│       ├── __init__.py     # Empty (package marker only)
│       ├── __main__.py     # Enable `python -m pyguard`
│       ├── cli.py          # CLI entry point (click)
│       ├── config.py       # Config loading logic
│       ├── constants.py    # Rule codes, default values, enums
│       └── types.py        # Common types and dataclasses
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Pytest fixtures
│   ├── test_config.py      # Config system tests
│   └── test_cli.py         # CLI integration tests
└── README.md
```

## Development Setup

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
pyguard --help
```

## Common Commands

```bash
# Run linter
pyguard lint .
pyguard lint src/

# Show configuration
pyguard config
pyguard config --json
pyguard config --validate

# Run tests
pytest

# Type checking
mypy src/

# Lint the codebase
ruff check src/
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

## Rule Codes

| Code | Description |
|------|-------------|
| TYP001 | Missing function parameter annotations |
| TYP002 | Missing function return annotation |
| TYP003 | Missing variable annotation |
| TYP010 | Disallow legacy typing syntax |
| KW001 | Require keyword-only parameters |
| RET001 | Disallow heterogeneous tuple returns |
| IMP001 | Disallow imports inside function bodies |
| EXP001 | Structured return types must be module-level |
| EXP002 | Enforce `__all__` or explicit re-export policy |

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

## Key Design Decisions

1. **Click for CLI** - Better UX, composable commands
2. **Dataclasses for config** - Minimal dependencies, immutable by default
3. **pyproject.toml only** - Consistent with modern Python tooling (ruff, black, mypy)
4. **Strict defaults** - Encourage best practices for typing rules

---

## Development Workflow

### Planning Structure

All work must follow a structured plan with three levels:
- **Chapters** - Major feature areas or milestones
- **Phases** - Groups of related steps within a chapter
- **Steps** - Minimal implementation units (the atomic work item)

See `DESIGN.md` Section 8 for the current implementation plan.

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
