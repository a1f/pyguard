#!/usr/bin/env bash
# Validate PyGuard installation and functionality
set -e

echo "=== PyGuard Validation Script ==="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
    else
        echo "No virtual environment found. Creating one..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -e ".[dev]" -q
    fi
fi

echo "Using Python: $(which python)"
echo

# 1. CLI Tests
echo "--- CLI Validation ---"

pyguard --help > /dev/null && pass "pyguard --help" || fail "pyguard --help"
pyguard --version > /dev/null && pass "pyguard --version" || fail "pyguard --version"
pyguard config > /dev/null && pass "pyguard config" || fail "pyguard config"
pyguard config --json > /dev/null && pass "pyguard config --json" || fail "pyguard config --json"
pyguard config --validate > /dev/null && pass "pyguard config --validate" || fail "pyguard config --validate"
pyguard lint . > /dev/null && pass "pyguard lint ." || fail "pyguard lint ."

echo

# 2. Test Suite
echo "--- Test Suite ---"
pytest -q && pass "pytest" || fail "pytest"

echo

# 3. Type Checking
echo "--- Type Checking ---"
mypy src/ && pass "mypy src/" || fail "mypy src/"

echo

# 4. Linting
echo "--- Linting ---"
ruff check src/ && pass "ruff check src/" || fail "ruff check src/"

echo
echo -e "${GREEN}=== All validations passed ===${NC}"
