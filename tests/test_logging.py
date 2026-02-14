"""Tests for --verbose and --debug logging flags."""
from __future__ import annotations

import contextlib
import logging
from collections.abc import Generator
from pathlib import Path

from click.testing import CliRunner

from pyguard.cli import cli


_SAMPLE_SOURCE: str = """\
def greet(name: str) -> None:
    print(name)
"""


class TestDefaultNoLogging:
    """Default mode should not emit logging output."""

    def test_lint_no_log_by_default(
        self, tmp_path: Path, caplog: logging.LogRecord,
    ) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with caplog.at_level(logging.DEBUG):  # type: ignore[union-attr]
            result = runner.invoke(cli, ["lint", str(tmp_path)])

        assert result.exit_code == 0
        # No pyguard log records at WARNING or above in normal output
        pyguard_warnings: list[str] = [
            r.message for r in caplog.records  # type: ignore[union-attr]
            if r.name.startswith("pyguard") and r.levelno >= logging.WARNING
        ]
        assert pyguard_warnings == []


class TestVerboseFlag:
    """--verbose shows INFO-level messages."""

    def test_verbose_lint_shows_file_count(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard") as records:
            runner.invoke(cli, ["--verbose", "lint", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "Found 1 files" in messages
        assert "Completed in" in messages

    def test_verbose_fix_shows_file_count(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard") as records:
            runner.invoke(cli, ["--verbose", "fix", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "Found 1 files to fix" in messages

    def test_verbose_does_not_corrupt_stdout(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        result = runner.invoke(
            cli, ["--verbose", "lint", "--format", "json", str(tmp_path)],
        )

        assert result.exit_code == 0
        # Stdout should not contain log prefixes
        assert "pyguard.runner:" not in result.output


class TestDebugFlag:
    """--debug shows DEBUG-level messages."""

    def test_debug_shows_per_file_detail(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard", level=logging.DEBUG) as records:
            runner.invoke(cli, ["--debug", "lint", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "Checking" in messages

    def test_debug_shows_rule_diagnostics(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard", level=logging.DEBUG) as records:
            runner.invoke(cli, ["--debug", "lint", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "diagnostics" in messages

    def test_debug_shows_scanner_exclusions(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text(_SAMPLE_SOURCE)
        cache_dir: Path = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text(_SAMPLE_SOURCE)

        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard", level=logging.DEBUG) as records:
            runner.invoke(cli, ["--debug", "lint", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "Excluded" in messages

    def test_debug_includes_info_messages(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(_SAMPLE_SOURCE)
        runner: CliRunner = CliRunner()
        with _capture_logs("pyguard", level=logging.DEBUG) as records:
            runner.invoke(cli, ["--debug", "lint", str(tmp_path)])

        messages: str = "\n".join(r.message for r in records)
        assert "Found" in messages
        assert "Completed in" in messages


class _LogCapture(logging.Handler):
    """Simple log handler that collects records."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@contextlib.contextmanager
def _capture_logs(
    name: str, *, level: int = logging.INFO,
) -> Generator[list[logging.LogRecord], None, None]:
    """Capture log records from a named logger."""
    handler = _LogCapture()
    handler.setLevel(level)
    log: logging.Logger = logging.getLogger(name)
    old_level: int = log.level
    log.setLevel(level)
    log.addHandler(handler)
    try:
        yield handler.records
    finally:
        log.removeHandler(handler)
        log.setLevel(old_level)
