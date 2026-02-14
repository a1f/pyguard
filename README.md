# PyGuard

A strict Python linter enforcing typing, keyword-only APIs, and structured returns.

## Installation

```bash
pip install pyguard
```

For autofix support (includes LibCST for complex transforms):

```bash
pip install pyguard[fix]
```

## Quick Start

```bash
# Lint Python files
pyguard lint src/

# Auto-fix issues
pyguard fix src/

# Preview fixes without writing
pyguard fix src/ --diff

# Check if files need fixing (CI mode)
pyguard fix src/ --check

# Learn about a rule
pyguard explain TYP001
```

## Commands

### `pyguard lint`

Run linting on Python files.

```bash
pyguard lint src/ tests/
pyguard lint --format json src/       # JSON output for CI/tooling
pyguard lint --no-show-source src/    # Suppress source snippets
pyguard lint --color never src/       # Disable colored output
```

### `pyguard fix`

Apply safe autofixes to Python files.

```bash
pyguard fix src/                # Fix files in-place
pyguard fix src/ --diff         # Print unified diff, don't write
pyguard fix src/ --check        # Exit 1 if changes needed (CI)
pyguard fix src/ --tryout       # Interactive: approve each fix
```

The `--tryout` mode shows a diff for each file and prompts:
- **y** — apply this fix
- **n** — skip this file
- **a** — apply all remaining without asking
- **q** — stop immediately

### `pyguard explain`

Show rule documentation and examples.

```bash
pyguard explain TYP001          # Detailed explanation of one rule
pyguard explain --all           # Summary table of all rules
```

### `pyguard config`

Show or validate configuration.

```bash
pyguard config                  # Show resolved config
pyguard config --json           # JSON output
pyguard config --validate       # Validate config file
```

## Global Flags

```bash
pyguard --config path/to/pyproject.toml lint src/   # Custom config path
pyguard --verbose lint src/                          # Show progress and timing
pyguard --debug lint src/                            # Detailed trace output
pyguard --version                                    # Show version
```

## Rules

| Code | Description | Default | Autofix |
|------|-------------|---------|---------|
| TYP001 | Missing function parameter annotations | error | - |
| TYP002 | Missing function return annotation | error | `-> None` |
| TYP003 | Missing variable annotation | warn | Infer type |
| TYP010 | Legacy typing syntax (`Optional`, `List`, etc.) | error | Full transform |
| KW001 | Missing keyword-only parameters | warn | Insert `*` |
| RET001 | Heterogeneous tuple returns | warn | - |
| IMP001 | In-function imports | error | Move to top |
| EXP001 | Module-level return types enforcement | off | - |
| EXP002 | Missing `__all__` declaration | off | - |

## Configuration

PyGuard is configured via `[tool.pyguard]` in `pyproject.toml`:

```toml
[tool.pyguard]
python_version = "3.11"
include = ["src/**/*.py", "tests/**/*.py"]
exclude = ["**/__pycache__/**"]
output_format = "text"  # "text" | "json"
show_source = true
color = "auto"  # "auto" | "always" | "never"

[tool.pyguard.rules]
TYP001 = "error"   # "error" | "warn" | "off"
TYP002 = "error"
TYP003 = "warn"
TYP010 = "error"
KW001 = "warn"
RET001 = "warn"
IMP001 = "error"
EXP001 = "off"
EXP002 = "off"

[tool.pyguard.rules.TYP001]
exempt_dunder = true
exempt_self_cls = true

[tool.pyguard.rules.TYP003]
scope = ["module"]  # "module", "class", "local"

[tool.pyguard.rules.KW001]
min_params = 2
exempt_dunder = true
exempt_private = true
exempt_overrides = true

[tool.pyguard.ignores]
require_reason = true
disallow = []
max_per_file = null  # null = unlimited
```

## Ignore Pragmas

Suppress diagnostics inline with a required reason:

```python
# Inline — suppress on the same line
x = 1  # pyguard: ignore[TYP003] because: legacy code

# Block — suppress the next statement
# pyguard: ignore[TYP001, TYP002] because: generated code
def foo(): ...

# File-level — suppress for the entire file
# pyguard: ignore-file[TYP003] because: data module
```

Governance rules enforce pragma discipline:
- **IGN001**: Ignore pragma missing required reason
- **IGN002**: Rule cannot be ignored (disallowed by config)
- **IGN003**: File exceeds maximum allowed ignore directives

## Pre-commit Integration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/your-org/pyguard
    rev: v0.1.0
    hooks:
      - id: pyguard-lint
      - id: pyguard-fix
```

## CI Integration

Example GitHub Actions workflow:

```yaml
name: PyGuard
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pyguard
      - run: pyguard fix --check src/
      - run: pyguard lint --format json src/ > pyguard-report.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: pyguard-report
          path: pyguard-report.json
```

## Development

```bash
# Clone and install
git clone https://github.com/your-org/pyguard.git
cd pyguard
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Run tests
.venv/bin/python -m pytest

# Type checking
.venv/bin/python -m mypy src/ --strict

# Lint
.venv/bin/python -m ruff check src/
```

## License

MIT
