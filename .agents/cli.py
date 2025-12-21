from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence
import os
import subprocess
import sys

import typer
import typer.completion as typer_completion

from .link_command import link_command as _link
from .db import (
    init_db,
    get_user_setting,
    set_user_setting,
    list_user_settings,
    remove_user_setting,
)

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Sub-CLI: settings
settings_app = typer.Typer(
    help="Manage user settings",
    context_settings={"help_option_names": ["-h", "--help"]},
)

_DEFAULT_COMPLETION_ALIAS = "zero"
_POWER_SHELL_NAMES = {"powershell", "pwsh"}


def _completion_aliases() -> list[str]:
    raw = os.getenv("ZEROLINK_COMPLETION_ALIASES")
    if raw is not None:
        raw = raw.replace(";", ",")
        parts = [part.strip() for part in raw.split(",") if part.strip()]
    elif os.name == "nt":
        parts = [_DEFAULT_COMPLETION_ALIAS]
    else:
        parts: list[str] = []
    seen: set[str] = set()
    unique: list[str] = []
    for alias in parts:
        key = alias.lower()
        if key not in seen:
            seen.add(key)
            unique.append(alias)
    return unique


def _resolve_shell(value: Optional[str]) -> str:
    if value and value != "auto":
        return value
    detector = getattr(typer_completion, "shellingham", None)
    if detector is not None:
        try:
            detected, _ = detector.detect_shell()
            if detected:
                return detected
        except Exception:
            pass
    if os.name == "nt":
        return "pwsh"
    raise typer.BadParameter(
        "Unable to detect the current shell automatically; pass the shell name explicitly."
    )


def _completion_prog_name(ctx: typer.Context) -> str:
    root = ctx.find_root()
    if root.info_name:
        return root.info_name
    return Path(sys.argv[0]).stem


def _completion_identifiers(ctx: typer.Context) -> tuple[str, str]:
    prog_name = _completion_prog_name(ctx)
    complete_var = f"_{prog_name.replace('-', '_').upper()}_COMPLETE"
    return prog_name, complete_var


def _inject_powershell_aliases(
    script: str, prog_name: str, aliases: Sequence[str]
) -> str:
    normalized: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        alias = alias.strip()
        if not alias or alias.lower() == prog_name.lower():
            continue
        key = alias.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(alias)
    if not normalized:
        return script
    lines = script.splitlines()
    try:
        insert_at = (
            lines.index(
                f"Register-ArgumentCompleter -Native -CommandName {prog_name} -ScriptBlock $scriptblock"
            )
            + 1
        )
    except ValueError:
        insert_at = len(lines)
    for alias in normalized:
        alias_line = (
            f"Register-ArgumentCompleter -Native -CommandName {alias} -ScriptBlock $scriptblock"
        )
        if alias_line in lines:
            continue
        lines.insert(insert_at, alias_line)
        insert_at += 1
    return "\n".join(lines)


def _render_completion_script(
    *, prog_name: str, complete_var: str, shell: str, aliases: Sequence[str]
) -> str:
    script = typer_completion.get_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell
    )
    if shell.lower() in _POWER_SHELL_NAMES:
        script = _inject_powershell_aliases(script, prog_name, aliases)
    return script


def _completion_payload(
    ctx: typer.Context, shell: str, aliases: Sequence[str]
) -> tuple[str, str, str]:
    prog_name, complete_var = _completion_identifiers(ctx)
    script = _render_completion_script(
        prog_name=prog_name, complete_var=complete_var, shell=shell, aliases=aliases
    )
    return prog_name, complete_var, script


def _install_powershell_completion(
    *,
    script: str,
    shell: str,
    prog_name: str,
    aliases: Sequence[str],
) -> Path:
    try:
        subprocess.run(
            [
                shell,
                "-Command",
                "Set-ExecutionPolicy",
                "Unrestricted",
                "-Scope",
                "CurrentUser",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        result = subprocess.run(
            [shell, "-NoProfile", "-Command", "Write-Output", "$profile"],
            check=True,
            stdout=subprocess.PIPE,
        )
    except FileNotFoundError:
        err = typer.style("[error]", fg=typer.colors.RED)
        typer.echo(f"{err} Shell executable '{shell}' was not found.")
        raise typer.Exit(code=1)
    raw_path = result.stdout
    if isinstance(raw_path, bytes):
        decoded = ""
        for encoding in ("utf-8", "utf-16", "utf-16le", "windows-1252", "cp850"):
            try:
                decoded = raw_path.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
            if decoded:
                break
        if not decoded:
            decoded = raw_path.decode("utf-8", errors="ignore").strip()
    else:
        decoded = str(raw_path).strip()
    if not decoded:
        err = typer.style("[error]", fg=typer.colors.RED)
        typer.echo(f"{err} Could not determine PowerShell profile path.")
        raise typer.Exit(code=1)
    profile_path = Path(decoded)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    existing = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    main_line = (
        f"Register-ArgumentCompleter -Native -CommandName {prog_name} -ScriptBlock $scriptblock"
    )
    alias_lines = [
        f"Register-ArgumentCompleter -Native -CommandName {alias} -ScriptBlock $scriptblock"
        for alias in aliases
        if alias.lower() != prog_name.lower()
    ]
    if existing and alias_lines:
        lines = existing.splitlines()
        present = set(lines)
        updated: list[str] = []
        changed = False
        for line in lines:
            updated.append(line)
            if line == main_line:
                for alias_line in alias_lines:
                    if alias_line not in present:
                        updated.append(alias_line)
                        present.add(alias_line)
                        changed = True
        if changed:
            text = "\n".join(updated)
            if not text.endswith("\n"):
                text += "\n"
            profile_path.write_text(text, encoding="utf-8")
            return profile_path
        if all(alias_line in present for alias_line in alias_lines):
            return profile_path
    block = script if script.endswith("\n") else f"{script}\n"
    with profile_path.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(block)
    return profile_path


def _perform_completion_install(
    ctx: typer.Context, value: Optional[str]
) -> tuple[str, Path]:
    shell = _resolve_shell(value)
    aliases = _completion_aliases()
    prog_name, complete_var, script = _completion_payload(ctx, shell, aliases)
    if shell.lower() in _POWER_SHELL_NAMES:
        path = _install_powershell_completion(
            script=script, shell=shell, prog_name=prog_name, aliases=aliases
        )
        return shell, path
    installed_shell, path = typer_completion.install(
        shell=shell, prog_name=prog_name, complete_var=complete_var
    )
    return installed_shell, path


def _show_completion_callback(ctx, param, value: Optional[str]):
    if not value or ctx.resilient_parsing:
        return value
    shell = _resolve_shell(value)
    aliases = _completion_aliases()
    _, _, script = _completion_payload(ctx, shell, aliases)
    typer.echo(script)
    raise typer.Exit()


def _install_completion_callback(ctx, param, value: Optional[str]):
    if not value or ctx.resilient_parsing:
        return value
    shell, path = _perform_completion_install(ctx, value)
    ok = typer.style("[ok]", fg=typer.colors.GREEN)
    typer.echo(f"{ok} Installed completion for {shell} -> {path}")
    raise typer.Exit()



@settings_app.command("list")
def settings_list() -> None:
    """List all settings as KEY=VALUE."""
    data = list_user_settings()
    for k in sorted(data.keys()):
        typer.echo(f"{k}={data[k]}")


@settings_app.command("get")
def settings_get(name: str) -> None:
    """Get a setting by key."""
    val = get_user_setting(name)
    if val is None:
        err = typer.style("[not found]", fg=typer.colors.YELLOW)
        typer.echo(f"{err} {name}")
        raise typer.Exit(code=1)
    typer.echo(val)


@settings_app.command("set")
def settings_set(name: str, value: str) -> None:
    """Set a KEY to VALUE."""
    set_user_setting(name, value)
    ok = typer.style("[ok]", fg=typer.colors.GREEN)
    typer.echo(f"{ok} {name}={value}")


@settings_app.command("rm")
def settings_remove(name: str) -> None:
    """Remove a setting by key."""
    if remove_user_setting(name):
        ok = typer.style("[ok]", fg=typer.colors.GREEN)
        typer.echo(f"{ok} removed {name}")
    else:
        warn = typer.style("[warn]", fg=typer.colors.YELLOW)
        typer.echo(f"{warn} {name} not set")


app.add_typer(settings_app, name="settings")

def _get_version() -> str:
    from ._version import VERSION as _V  # type: ignore
    return str(_V)


def _scripts_dir() -> Path:
    exe = Path(sys.argv[0]).resolve()
    return exe.parent if exe.exists() else Path(sys.executable).resolve().parent


def _ensure_windows_cmd_alias(alias_name: str, target_exe_name: str) -> Path | None:
    if os.name != "nt":
        return None
    scripts = _scripts_dir()
    dest = scripts / f"{alias_name}.cmd"
    content = f"@echo off\r\n\"%~dp0{target_exe_name}\" %*\r\n"
    current = dest.read_text(encoding="ascii") if dest.exists() else None
    if current != content:
        dest.write_text(content, encoding="ascii")
    return dest


def _version_callback(value: Optional[bool]) -> None:
    if value:
        typer.echo(f"zerolink {_get_version()}")
        raise typer.Exit()


def _init_callback(value: Optional[bool]) -> None:
    if value:
        path = init_db()
        ok = typer.style("[ok]", fg=typer.colors.GREEN)
        info = typer.style("[info]", fg=typer.colors.BRIGHT_BLACK)
        typer.echo(f"{ok} database initialized")
        typer.echo(f"{info} path: {path}")
        # Create a convenience alias 'zero' next to the installed executable on Windows
        alias_path = _ensure_windows_cmd_alias(alias_name="zero", target_exe_name="zerolink.exe")
        if alias_path is not None:
            typer.echo(f"{ok} alias created: {alias_path}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _show_completion: Optional[str] = typer.Option(
        None,
        "--show-completion",
        help="Show the shell completion script and exit.",
        callback=_show_completion_callback,
        is_eager=True,
        flag_value="auto",
        expose_value=False,
    ),
    _install_completion: Optional[str] = typer.Option(
        None,
        "--install-completion",
        help="Install shell completion for the current shell and exit.",
        callback=_install_completion_callback,
        is_eager=True,
        flag_value="auto",
        expose_value=False,
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
    init: Optional[bool] = typer.Option(
        None,
        "--init",
        help="Initialize local database and exit",
        callback=_init_callback,
        is_eager=True,
    ),
) -> None:
    """Zero CLI root. Use subcommands like `link` or `settings`."""
    if ctx.invoked_subcommand:
        return
    # No subcommand -> show help
    typer.echo(ctx.get_help())
    raise typer.Exit()


@app.command("link", context_settings={"help_option_names": ["-h", "--help"]})
def link(
    src: Path = typer.Argument(..., help="Target directory the link should point to"),
    dst: Path = typer.Argument(..., help="Path where symlink should be created/replace"),
) -> None:
    """Create or replace a symlink at DST pointing to SRC."""
    _link(src=src, dst=dst)


# Removed implicit alias subcommands per preference (no fallbacks/aliases)
