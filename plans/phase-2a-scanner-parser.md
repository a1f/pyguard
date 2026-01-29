# Phase 2A: File Scanner + AST Parser

## Scope

Build the file discovery and AST parsing foundation. No diagnostics, no formatters, no CLI integration yet.

**Exit Criteria**: Unit tests pass for file scanning and AST parsing modules.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Entry Points                            │
│                    (CLI - not in this phase)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         scanner.py                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  scan_files(paths, config) -> list[Path]                  │  │
│  │                                                           │  │
│  │  1. Expand input paths (files/directories)                │  │
│  │  2. Recursively find all .py files                        │  │
│  │  3. Apply include patterns (glob matching)                │  │
│  │  4. Apply exclude patterns (glob matching)                │  │
│  │  5. Return sorted, deduplicated list                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         parser.py                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  parse_file(file) -> ParseResult                          │  │
│  │                                                           │  │
│  │  1. Read file content (handle encoding/IO errors)         │  │
│  │  2. Split into source lines                               │  │
│  │  3. Parse with ast.parse()                                │  │
│  │  4. Capture SyntaxError if parsing fails                  │  │
│  │  5. Return ParseResult with tree or error info            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Input Paths          Config
     │                  │
     ▼                  ▼
┌────────────────────────────┐
│        scan_files()        │
│  paths + include/exclude   │
└────────────────────────────┘
              │
              ▼
       list[Path]  ──────────┐
                             │
              ┌──────────────┘
              ▼
       ┌─────────────┐
       │ parse_file()│ ◄── called per file
       └─────────────┘
              │
              ▼
       ParseResult
       ├─ file: Path
       ├─ tree: ast.Module | None
       ├─ source: str
       ├─ source_lines: tuple[str, ...]
       └─ syntax_error: SyntaxErrorInfo | None
```

---

## Module Design

### `src/pyguard/scanner.py` (~60 lines)

**Purpose**: Discover Python files matching config patterns.

**Public API**:
```
scan_files(*, paths: tuple[Path, ...], config: PyGuardConfig) -> list[Path]
```

**Internal functions**:
- `_collect_python_files(path, base) -> list[Path]` - recursive file collection
- `_matches_pattern(path, patterns, base) -> bool` - glob pattern matching

**Dependencies**: `pathlib`, `fnmatch`, `pyguard.types.PyGuardConfig`

---

### `src/pyguard/parser.py` (~80 lines)

**Purpose**: Parse Python files into AST, capture syntax errors.

**Data structures**:
```
@dataclass(frozen=True, slots=True)
class SyntaxErrorInfo:
    line: int           # 1-based
    column: int         # 1-based
    message: str
    source_line: str | None

@dataclass(frozen=True, slots=True)
class ParseResult:
    file: Path
    tree: ast.Module | None
    source: str
    source_lines: tuple[str, ...]
    syntax_error: SyntaxErrorInfo | None
```

**Public API**:
```
parse_file(*, file: Path) -> ParseResult
```

**Dependencies**: `ast`, `pathlib`, dataclasses

---

## Commit Plan

### Commit 1: Scanner Module (~60 lines code + ~100 lines tests)

**Files**:
- `src/pyguard/scanner.py` (new)
- `tests/test_scanner.py` (new)

**Implementation**:
1. Create `scanner.py` with `scan_files()` function
2. Handle single files and directories
3. Recursive `.py` file discovery
4. Include/exclude pattern matching using `fnmatch`
5. Return sorted, deduplicated paths

**Validation**:
```bash
# Tests pass
pytest tests/test_scanner.py -v

# Type check passes
mypy src/pyguard/scanner.py --strict

# Lint passes
ruff check src/pyguard/scanner.py

# Manual verification
python -c "
from pathlib import Path
from pyguard.scanner import scan_files
from pyguard.types import PyGuardConfig

# Test with src directory
config = PyGuardConfig()
files = scan_files(paths=(Path('src'),), config=config)
print(f'Found {len(files)} files')
for f in files[:5]:
    print(f'  {f}')

# Verify exclusions work
assert not any('__pycache__' in str(f) for f in files)
assert not any('.git' in str(f) for f in files)
print('All exclusions working')
"
```

---

### Commit 2: Parser Module (~80 lines code + ~80 lines tests)

**Files**:
- `src/pyguard/parser.py` (new)
- `tests/test_parser.py` (new)

**Implementation**:
1. Create `SyntaxErrorInfo` and `ParseResult` dataclasses
2. Implement `parse_file()` function
3. Handle file read errors (OSError, UnicodeDecodeError)
4. Handle syntax errors from `ast.parse()`
5. Extract line/column/message from SyntaxError

**Validation**:
```bash
# Tests pass
pytest tests/test_parser.py -v

# Type check passes
mypy src/pyguard/parser.py --strict

# Lint passes
ruff check src/pyguard/parser.py

# Manual verification - valid file
python -c "
from pathlib import Path
from pyguard.parser import parse_file

result = parse_file(file=Path('src/pyguard/constants.py'))
assert result.tree is not None
assert result.syntax_error is None
print(f'Parsed {result.file}: {len(result.source_lines)} lines')
print(f'AST has {len(result.tree.body)} top-level nodes')
"

# Manual verification - syntax error
python -c "
from pathlib import Path
from pyguard.parser import parse_file
import tempfile

# Create file with syntax error
with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w') as f:
    f.write('def broken(\n')
    bad_file = Path(f.name)

result = parse_file(file=bad_file)
assert result.tree is None
assert result.syntax_error is not None
print(f'Syntax error at line {result.syntax_error.line}')
print(f'Message: {result.syntax_error.message}')
bad_file.unlink()
"
```

---

## Test Coverage

### `tests/test_scanner.py`

| Test | Description |
|------|-------------|
| `test_scan_single_file` | Single .py file returns that file |
| `test_scan_non_python_file` | Non-.py files excluded |
| `test_scan_directory` | Directory recursively scanned |
| `test_exclude_pycache` | `__pycache__` excluded by default |
| `test_exclude_dotfiles` | Hidden files/dirs excluded |
| `test_include_pattern` | Only matching patterns included |
| `test_exclude_pattern` | Excluded patterns filtered out |
| `test_multiple_paths` | Multiple input paths combined |
| `test_results_sorted` | Output is deterministically sorted |
| `test_empty_directory` | Empty dir returns empty list |

### `tests/test_parser.py`

| Test | Description |
|------|-------------|
| `test_parse_valid_file` | Valid code produces AST |
| `test_parse_empty_file` | Empty file produces empty AST |
| `test_syntax_error_captured` | Syntax error info extracted |
| `test_syntax_error_location` | Line/column correct |
| `test_file_not_found` | Missing file handled gracefully |
| `test_unicode_content` | UTF-8 content parsed |
| `test_encoding_error` | Invalid encoding handled |
| `test_source_lines_preserved` | Source split correctly |

---

## Code Conventions

- `from __future__ import annotations` at top
- `@dataclass(frozen=True, slots=True)` for immutable data
- All functions use `*` for keyword-only parameters
- All variables have type annotations
- Modern typing: `list[str]` not `List[str]`
