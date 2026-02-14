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

## Try It on Real Projects

The `examples/` directory includes two open-source projects for hands-on testing.
Clone them and run PyGuard to see what it finds and what it can fix.

### Setup

```bash
git clone https://github.com/your-org/pyguard.git
cd pyguard
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Clone example projects
git clone --depth 1 https://github.com/suurjaak/pyscripts.git examples/pyscripts
git clone --depth 1 https://github.com/cdeil/python-cli-examples.git examples/python-cli-examples
```

### 1. pyscripts — untyped utility scripts

Nine small Python scripts with zero type annotations (~100-350 lines each).
Exercises TYP001, TYP002, TYP003, KW001.

```bash
# Lint — see all diagnostics
pyguard lint examples/pyscripts/
# Expected: ~146 errors, ~47 warnings across 8 files

# Preview what the fixer would change
pyguard fix examples/pyscripts/ --diff

# Walk through fixes interactively
pyguard fix examples/pyscripts/ --tryout

# Apply all fixes at once
pyguard fix examples/pyscripts/

# Re-lint to see what's left (parameter annotations are not auto-fixed)
pyguard lint examples/pyscripts/
```

What the fixer does here:
- Adds `-> None` return annotations to functions that don't return (TYP002)
- Adds type annotations to module-level variables like `result: str = ...` (TYP003)

What stays unfixed (needs manual work):
- Missing parameter annotations (TYP001) — too ambiguous to infer
- Keyword-only parameter suggestions (KW001) — API-breaking change
- 2 files with Python 2 syntax errors (SYN001) — skipped safely

### 2. python-cli-examples — CLI demo scripts

Small CLI examples using argparse, click, and cliff. Missing type annotations
and some in-function imports. Exercises TYP001, TYP002, IMP001.

```bash
# Lint — see all diagnostics
pyguard lint examples/python-cli-examples/
# Expected: ~41 errors, ~7 warnings across 19 files

# Preview fixes
pyguard fix examples/python-cli-examples/ --diff

# Apply fixes
pyguard fix examples/python-cli-examples/

# Re-lint to see remaining issues
pyguard lint examples/python-cli-examples/
```

What the fixer does here:
- Adds `-> None` to functions and test methods (TYP002)
- Moves in-function imports to the top of the file (IMP001) — e.g. in
  `argparse/greet/cli/main.py`, `from .hello import ...` gets moved out
  of `main()` to module level

### 3. Self-lint

PyGuard's own codebase passes clean (zero errors, warnings only for
overridden external methods and library compatibility):

```bash
pyguard lint src/
# Expected: 0 errors, a few KW001 warnings for LibCST/Click overrides.
#           Checked 33 files. Exit code 0.
```

## Development

```bash
# Clone and install
git clone https://github.com/your-org/pyguard.git
cd pyguard
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

# Run tests (503 tests)
.venv/bin/python -m pytest

# Type checking
.venv/bin/python -m mypy src/ --strict

# Lint
.venv/bin/python -m ruff check src/

# Full validation gate
.venv/bin/python -m pytest --tb=short -q && \
.venv/bin/python -m mypy src/ --strict && \
.venv/bin/python -m ruff check src/
```

## License

MIT
