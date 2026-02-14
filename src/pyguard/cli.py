"""Command-line interface for PyGuard using Click."""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Final

import click

from pyguard.config import load_config
from pyguard.constants import DEFAULT_SEVERITIES, ColorMode, OutputFormat, __version__
from pyguard.explain import RULE_CATALOG, format_rule_detail, format_rule_table
from pyguard.runner import FixResult, fix_paths, format_diff, format_results, lint_paths
from pyguard.types import ConfigError, PyGuardConfig


def format_config_text(*, config: PyGuardConfig) -> str:
    """Format configuration as human-readable text."""
    lines: list[str] = [
        "PyGuard Configuration",
        "=" * 40,
        "",
        f"Config file: {config.config_path or '(defaults)'}",
        f"Python version: {config.python_version}",
        "",
        "File Discovery:",
        f"  Include: {', '.join(config.include)}",
        f"  Exclude: {', '.join(config.exclude[:5])}{'...' if len(config.exclude) > 5 else ''}",
        "",
        "Output:",
        f"  Format: {config.output_format.value}",
        f"  Color: {config.color.value}",
        f"  Show source: {config.show_source}",
        "",
        "Rule Severities:",
    ]

    for code, severity in sorted(config.rules.severities.items()):
        status: str = severity.value.upper()
        lines.append(f"  {code}: {status}")

    max_display: str | int = (
        config.ignores.max_per_file if config.ignores.max_per_file is not None else "unlimited"
    )
    lines.extend([
        "",
        "Ignore Governance:",
        f"  Require reason: {config.ignores.require_reason}",
        f"  Disallow: {sorted(config.ignores.disallow) or '(none)'}",
        f"  Max per file: {max_display}",
    ])

    return "\n".join(lines)


def format_config_json(*, config: PyGuardConfig) -> str:
    """Format configuration as JSON."""
    data: dict[str, Any] = {
        "config_path": str(config.config_path) if config.config_path else None,
        "python_version": config.python_version,
        "include": list(config.include),
        "exclude": list(config.exclude),
        "output_format": config.output_format.value,
        "show_source": config.show_source,
        "color": config.color.value,
        "rules": {
            "severities": {
                code: sev.value for code, sev in config.rules.severities.items()
            },
            "TYP001": {
                "exempt_dunder": config.rules.typ001.exempt_dunder,
                "exempt_self_cls": config.rules.typ001.exempt_self_cls,
            },
            "TYP003": {
                "scope": [s.value for s in config.rules.typ003.scope],
            },
            "KW001": {
                "min_params": config.rules.kw001.min_params,
                "exempt_dunder": config.rules.kw001.exempt_dunder,
                "exempt_private": config.rules.kw001.exempt_private,
                "exempt_overrides": config.rules.kw001.exempt_overrides,
            },
        },
        "ignores": {
            "require_reason": config.ignores.require_reason,
            "disallow": sorted(config.ignores.disallow),
            "max_per_file": config.ignores.max_per_file,
        },
    }
    return json.dumps(data, indent=2)


class ConfigType(click.ParamType):
    """Custom Click parameter type for config path."""

    name: str = "path"

    def convert(
        self,
        value: str | Path | None,
        param: click.Parameter | None,
        ctx: click.Context | None,
    ) -> Path | None:
        if value is None:
            return None
        return Path(value)


CONFIG_TYPE: Final[ConfigType] = ConfigType()


@click.group()
@click.version_option(version=__version__, prog_name="pyguard")
@click.option(
    "--config",
    "config_path",
    type=CONFIG_TYPE,
    default=None,
    help="Path to pyproject.toml (default: search upward from current directory)",
)
@click.option("--verbose", is_flag=True, help="Show progress and timing")
@click.option("--debug", is_flag=True, help="Show detailed trace")
@click.pass_context
def cli(
    ctx: click.Context,
    *,
    config_path: Path | None,
    verbose: bool,
    debug: bool,
) -> None:
    """PyGuard - A strict Python linter for typing, APIs, and structured returns."""
    level: int = (
        logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    )
    logging.basicConfig(
        level=level,
        format="%(name)s: %(message)s",
        stream=sys.stderr,
    )

    ctx.ensure_object(dict)
    try:
        cfg: PyGuardConfig = load_config(path=config_path)
        ctx.obj["config"] = cfg
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        if e.path:
            click.echo(f"  in: {e.path}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--validate", is_flag=True, help="Only validate configuration, don't print")
@click.option("--json", "as_json", is_flag=True, help="Output configuration as JSON")
@click.pass_context
def config(ctx: click.Context, *, validate: bool, as_json: bool) -> None:
    """Show or validate configuration."""
    cfg: PyGuardConfig = ctx.obj["config"]

    if validate:
        click.echo(f"Configuration valid: {cfg.config_path or '(defaults)'}")
        return

    if as_json:
        click.echo(format_config_json(config=cfg))
    else:
        click.echo(format_config_text(config=cfg))


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default=None,
    help="Output format (overrides config)",
)
@click.option(
    "--color",
    type=click.Choice(["auto", "always", "never"]),
    default=None,
    help="Color output mode (overrides config)",
)
@click.option("--show-source/--no-show-source", default=None, help="Show source code snippets")
@click.pass_context
def lint(
    ctx: click.Context,
    paths: tuple[Path, ...],
    *,
    output_format: str | None,
    color: str | None,
    show_source: bool | None,
) -> None:
    """Run linting on Python files."""
    cfg: PyGuardConfig = ctx.obj["config"]

    # Apply CLI overrides
    overrides: dict[str, Any] = {}
    if output_format is not None:
        overrides["output_format"] = OutputFormat(output_format)
    if color is not None:
        overrides["color"] = ColorMode(color)
    if show_source is not None:
        overrides["show_source"] = show_source

    if overrides:
        cfg = replace(cfg, **overrides)

    if not paths:
        paths = (Path("."),)

    result = lint_paths(paths=paths, config=cfg)
    output: str = format_results(result=result, config=cfg)
    if output:
        click.echo(output)
    ctx.exit(result.exit_code)


@cli.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--diff", "show_diff", is_flag=True, help="Print unified diff, don't write files")
@click.option("--check", "check_only", is_flag=True, help="Exit 1 if any file would change")
@click.pass_context
def fix(
    ctx: click.Context,
    paths: tuple[Path, ...],
    *,
    show_diff: bool,
    check_only: bool,
) -> None:
    """Apply safe autofixes to Python files."""
    cfg: PyGuardConfig = ctx.obj["config"]

    if not paths:
        paths = (Path("."),)

    result: FixResult = fix_paths(paths=paths, config=cfg)

    if show_diff:
        for path in sorted(result.changes):
            old, new = result.changes[path]
            click.echo(format_diff(path=path, old=old, new=new), nl=False)
        suffix: str = "s" if result.files_changed != 1 else ""
        click.echo(f"{result.files_changed} file{suffix} would be changed.")
        return

    if check_only:
        suffix = "s" if result.files_changed != 1 else ""
        if result.files_changed > 0:
            click.echo(f"{result.files_changed} file{suffix} would be changed.")
            ctx.exit(1)
        else:
            click.echo("No changes needed.")
        return

    # Default: write changed files in-place
    for path, (_, new) in result.changes.items():
        path.write_text(new, encoding="utf-8")

    suffix = "s" if result.files_changed != 1 else ""
    click.echo(f"Fixed {result.files_changed} file{suffix}.")


@cli.command()
@click.argument("rule_code", required=False, default=None)
@click.option("--all", "show_all", is_flag=True, help="List all rules with summaries")
@click.pass_context
def explain(ctx: click.Context, rule_code: str | None, *, show_all: bool) -> None:
    """Show rule documentation and examples."""
    cfg: PyGuardConfig = ctx.obj["config"]

    if show_all:
        severities: dict[str, str] = {
            code: sev.value for code, sev in cfg.rules.severities.items()
        }
        click.echo(format_rule_table(catalog=RULE_CATALOG, severities=severities))
        return

    if rule_code is None:
        click.echo("Usage: pyguard explain <RULE_CODE> or pyguard explain --all")
        ctx.exit(1)
        return

    code: str = rule_code.upper()
    if code not in RULE_CATALOG:
        click.echo(f"Error: Unknown rule code '{code}'.", err=True)
        ctx.exit(1)
        return

    sev = DEFAULT_SEVERITIES.get(code)
    severity_str: str = sev.value if sev is not None else "off"
    click.echo(format_rule_detail(
        info=RULE_CATALOG[code],
        default_severity=severity_str,
    ))


def main() -> None:
    """Main entry point for pyguard CLI."""
    cli()


if __name__ == "__main__":
    main()
