# PyGuard

A strict Python linter enforcing typing, keyword-only APIs, and structured returns.

## Installation

```bash
pip install pyguard
```

## Usage

```bash
# Run linter
pyguard lint .
pyguard lint src/

# Show configuration
pyguard config
pyguard config --json
pyguard config --validate
```

## Configuration

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
TYP001 = "error"   # Missing function parameter annotations
TYP002 = "error"   # Missing function return annotation
TYP003 = "warn"    # Missing variable annotation
KW001 = "warn"     # Require keyword-only parameters
```

## License

MIT
