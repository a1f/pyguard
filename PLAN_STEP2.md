# PyGuard Step 2: Parser + File Walker + Diagnostic Model

## Overview

Build the linting infrastructure: file discovery, AST parsing, diagnostic model, and output formatting.

**Exit Criteria**: `pyguard lint path/` produces deterministic diagnostics for syntax errors.

## Design Decisions (from user)

- Infrastructure + syntax errors only (no rules yet)
- Separate modules: scanner.py, parser.py, diagnostics.py, formatters.py, runner.py
- Exit code: 1 for error-severity violations, 0 otherwise
- Sequential file processing (no parallelism)
- Click's built-in styling for colors
- Syntax errors = ERROR severity

---

## Files to Create

### 1. `src/pyguard/diagnostics.py`

Diagnostic data model.

```python
@dataclass(frozen=True, slots=True)
class SourceLocation:
    line: int              # 1-based
    column: int            # 1-based
    end_line: int | None = None
    end_column: int | None = None

@dataclass(frozen=True, slots=True)
class Diagnostic:
    file: Path
    location: SourceLocation
    code: str              # e.g., "SYN001", "TYP001"
    message: str
    severity: Severity
    source_line: str | None = None

@dataclass(slots=True)
class DiagnosticCollection:
    # Mutable collection for accumulating diagnostics
    # Methods: add(), add_all(), has_errors(), diagnostics (sorted property)
```

### 2. `src/pyguard/scanner.py`

File discovery using glob patterns.

```python
def scan_files(*, paths: tuple[Path, ...], config: PyGuardConfig) -> list[Path]:
    """Find Python files matching include/exclude patterns. Returns sorted list."""
```

### 3. `src/pyguard/parser.py`

AST parsing with syntax error detection.

```python
SYNTAX_ERROR_CODE: str = "SYN001"

@dataclass(frozen=True, slots=True)
class ParseResult:
    file: Path
    tree: ast.Module | None      # None if syntax error
    source: str
    source_lines: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]

def parse_file(*, file: Path) -> ParseResult:
    """Parse Python file, capture syntax errors as diagnostics."""
```

### 4. `src/pyguard/formatters.py`

Output formatters for text/JSON/GitHub.

```python
class TextFormatter:
    def format(*, diagnostics: DiagnosticCollection, config: PyGuardConfig) -> str

class JsonFormatter:
    def format(*, diagnostics: DiagnosticCollection, config: PyGuardConfig) -> str

class GithubFormatter:
    def format(*, diagnostics: DiagnosticCollection, config: PyGuardConfig) -> str

def get_formatter(*, output_format: OutputFormat) -> Formatter
def format_summary(*, diagnostics: DiagnosticCollection) -> str
```

### 5. `src/pyguard/runner.py`

Main orchestrator.

```python
@dataclass(frozen=True, slots=True)
class LintResult:
    diagnostics: DiagnosticCollection
    files_checked: int
    exit_code: int  # 0 = success, 1 = errors

def lint_paths(*, paths: tuple[Path, ...], config: PyGuardConfig) -> LintResult
def format_results(*, result: LintResult, config: PyGuardConfig) -> str
```

---

## Files to Modify

### `src/pyguard/cli.py`

Replace placeholder `lint` command with:

```python
def lint(...) -> None:
    from pyguard.runner import lint_paths, format_results

    # ... apply CLI overrides ...

    result = lint_paths(paths=paths, config=cfg)
    output = format_results(result=result, config=cfg)
    if output:
        click.echo(output)
    ctx.exit(result.exit_code)
```

### `src/pyguard/constants.py`

Add syntax error code:

```python
SYNTAX_ERROR_CODE: Final[str] = "SYN001"
```

---

## Implementation Order

1. **diagnostics.py** - No dependencies, foundation for all modules
2. **scanner.py** - Depends on types.py only
3. **parser.py** - Depends on diagnostics.py, constants.py
4. **formatters.py** - Depends on diagnostics.py, constants.py, types.py
5. **runner.py** - Depends on all above
6. **cli.py update** - Depends on runner.py

---

## Test Files to Create

| File | Tests |
|------|-------|
| `tests/test_diagnostics.py` | SourceLocation, Diagnostic, DiagnosticCollection |
| `tests/test_scanner.py` | File discovery, include/exclude patterns |
| `tests/test_parser.py` | Valid parsing, syntax errors, file read errors |
| `tests/test_formatters.py` | Text/JSON/GitHub output, summary |
| `tests/test_runner.py` | End-to-end linting, exit codes |
| `tests/test_lint_cli.py` | CLI integration tests |

---

## Example Output

### Text Format
```
src/example.py:3:5: ERROR [SYN001] Syntax error: expected ':'
  def broken(
      ^

Found 1 error.
Checked 5 files.
```

### JSON Format
```json
[
  {
    "file": "src/example.py",
    "line": 3,
    "column": 5,
    "code": "SYN001",
    "severity": "error",
    "message": "Syntax error: expected ':'",
    "source_line": "def broken("
  }
]
```

### GitHub Format
```
::error file=src/example.py,line=3,col=5::[SYN001] Syntax error: expected ':'
```

---

## Code Conventions (from Step 1)

- `from __future__ import annotations` at top
- `@dataclass(frozen=True, slots=True)` for immutable data
- All functions use `*` for keyword-only parameters
- All variables have type annotations
- No `TYPE_CHECKING` blocks - import directly
- Modern typing: `list[str]` not `List[str]`, `X | None` not `Optional[X]`

---

## Verification

After implementation:

```bash
# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/

# Manual verification
pyguard lint .                          # Should work on valid code
pyguard lint --format json .            # JSON output
pyguard lint --format github .          # GitHub annotations

# Create a file with syntax error and verify detection
echo "def broken(" > /tmp/bad.py
pyguard lint /tmp/bad.py                # Should show SYN001 error, exit 1
```

---

## Files Summary

| File | Est. Lines | Description |
|------|------------|-------------|
| `src/pyguard/diagnostics.py` | 80 | Diagnostic dataclasses |
| `src/pyguard/scanner.py` | 60 | File discovery |
| `src/pyguard/parser.py` | 70 | AST parsing |
| `src/pyguard/formatters.py` | 150 | Output formatters |
| `src/pyguard/runner.py` | 80 | Orchestrator |
| `tests/test_diagnostics.py` | 100 | Diagnostic tests |
| `tests/test_scanner.py` | 100 | Scanner tests |
| `tests/test_parser.py` | 80 | Parser tests |
| `tests/test_formatters.py` | 150 | Formatter tests |
| `tests/test_runner.py` | 80 | Runner tests |
| `tests/test_lint_cli.py` | 100 | CLI integration tests |

**Total**: ~1050 lines new code + tests
