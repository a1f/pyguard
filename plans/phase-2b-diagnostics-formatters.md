# Phase 2B: Diagnostic Structure + Formatters

## Scope

Define the `Diagnostic` data model and implement text/JSON formatters. No runner, no CLI changes, no conversion from `SyntaxErrorInfo` yet.

**Exit Criteria**: Unit tests pass for diagnostics and formatters modules.

---

## Why Diagnostics?

The `Diagnostic` structure is a **uniform container** for any issue found in code:

| Source | Example Code | Produces |
|--------|--------------|----------|
| Parser | SYN001 | Syntax errors |
| Type rules | TYP001, TYP002 | Missing annotations |
| Style rules | KW001 | Keyword-only params |

Without this, each rule would have its own structure and formatters couldn't work generically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         diagnostics.py                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  SourceLocation (line, column, end_line, end_column)          │  │
│  │  Diagnostic (file, location, code, message, severity, source) │  │
│  │  DiagnosticCollection (add, has_errors, sorted diagnostics)   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         formatters.py                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Formatter (Protocol)                                         │  │
│  │  TextFormatter.format(diagnostics, config) -> str             │  │
│  │  JsonFormatter.format(diagnostics, config) -> str             │  │
│  │  get_formatter(output_format) -> Formatter                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow (Future Integration)

```
ParseResult.syntax_error ───► [conversion in runner] ───► Diagnostic
                                                              │
rules(ParseResult.tree) ────────────────────────────────► Diagnostic
                                                              │
                                                              ▼
                                                   DiagnosticCollection
                                                              │
                                                              ▼
                                                   Formatter.format()
                                                              │
                                                              ▼
                                                         Output string
```

---

## Module Design

### `src/pyguard/diagnostics.py` (~60 lines)

**Classes:**
- `SourceLocation` - line, column, end_line, end_column (1-based)
- `Diagnostic` - file, location, code, message, severity, source_line
- `DiagnosticCollection` - mutable container with add(), has_errors(), error_count, warning_count

### `src/pyguard/formatters.py` (~100 lines)

**Classes:**
- `Formatter` - Protocol defining format() method
- `TextFormatter` - human-readable output (path:line:col: SEVERITY [CODE] message)
- `JsonFormatter` - JSON array output

**Functions:**
- `get_formatter()` - factory returning formatter by OutputFormat
- `format_summary()` - "Found X errors, Y warnings"

---

## Example Output

### Text Format
```
src/example.py:3:5: ERROR [SYN001] Syntax error: expected ':'
    def broken(
        ^

src/other.py:10:1: WARN [TYP001] Missing type annotation for parameter 'x'
    def foo(x):
    ^

Found 1 error, 1 warning in 2 files.
```

### JSON Format
```json
[
  {
    "file": "src/example.py",
    "line": 3,
    "column": 5,
    "end_line": null,
    "end_column": null,
    "code": "SYN001",
    "severity": "error",
    "message": "Syntax error: expected ':'",
    "source_line": "def broken("
  }
]
```

---

## Commit Plan

### Commit 1: Diagnostics Module (~60 lines code + ~80 lines tests)

**Files**:
- `src/pyguard/diagnostics.py` (new)
- `tests/test_diagnostics.py` (new)

**Tests**:
| Test | Description |
|------|-------------|
| `test_source_location_creation` | Basic location with line/column |
| `test_source_location_with_end` | Location with end position |
| `test_diagnostic_creation` | Create diagnostic with all fields |
| `test_diagnostic_frozen` | Verify immutability |
| `test_collection_add` | Add single diagnostic |
| `test_collection_add_all` | Add multiple diagnostics |
| `test_collection_sorted` | Diagnostics sorted by file, line, col |
| `test_collection_has_errors` | True when ERROR severity present |
| `test_collection_counts` | error_count, warning_count correct |
| `test_collection_empty` | Empty collection behavior |

**Validation**:
```bash
pytest tests/test_diagnostics.py -v
mypy src/pyguard/diagnostics.py --strict
ruff check src/pyguard/diagnostics.py
```

---

### Commit 2: Formatters Module (~100 lines code + ~100 lines tests)

**Files**:
- `src/pyguard/formatters.py` (new)
- `tests/test_formatters.py` (new)

**Tests**:
| Test | Description |
|------|-------------|
| `test_text_single_diagnostic` | Format one diagnostic |
| `test_text_multiple_diagnostics` | Format several diagnostics |
| `test_text_with_source_line` | Include source and caret |
| `test_text_without_source` | show_source=False |
| `test_text_summary` | "Found X errors, Y warnings" |
| `test_json_single_diagnostic` | JSON with one item |
| `test_json_multiple_diagnostics` | JSON array |
| `test_json_null_fields` | Null for missing end positions |
| `test_get_formatter_text` | Factory returns TextFormatter |
| `test_get_formatter_json` | Factory returns JsonFormatter |

**Validation**:
```bash
pytest tests/test_formatters.py -v
mypy src/pyguard/formatters.py --strict
ruff check src/pyguard/formatters.py
```

---

## Code Conventions

- `from __future__ import annotations` at top
- `@dataclass(frozen=True, slots=True)` for immutable data
- `@dataclass(slots=True)` for mutable collection (not frozen)
- All functions use `*` for keyword-only parameters
- Modern typing: `list[str]` not `List[str]`
