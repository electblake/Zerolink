from __future__ import annotations
import os
import shutil
from pathlib import Path

import typer
from sqlalchemy import select
from zerolink.db import get_session, RuleSource, Rule

def norm_path(p: str | Path) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("init")
def init_command() -> None:
    with get_session() as s:
        s.flush()
    typer.echo("initialized global database")


rules = typer.Typer(help="Manage directory linking rules")
app.add_typer(rules, name="rules")


@rules.command("add")
def rules_add(source_dir: Path = typer.Argument(...), target_dir: Path = typer.Argument(...)) -> None:
    sd = norm_path(source_dir)
    td = norm_path(target_dir)
    rid = os.stat(sd).st_ino
    tid = os.stat(td).st_ino
    with get_session() as s:
        src = s.get(RuleSource, rid)
        if src is None:
            src = RuleSource(source_inode=rid, recent_name=sd.name, parent_dir=str(sd.parent))
            s.add(src)
        else:
            src.recent_name = sd.name
            src.parent_dir = str(sd.parent)

        rule = s.get(Rule, {"source_inode": rid, "target_inode": tid})
        if rule is None:
            s.add(Rule(source_inode=rid, target_inode=tid, target_name=td.name, target_path=str(td)))
        else:
            rule.target_name = td.name
            rule.target_path = str(td)
        s.commit()
    typer.echo(f"rule added: {sd} -> {td}")


@rules.command("ls")
def rules_list() -> None:
    with get_session() as s:
        for src in s.scalars(select(RuleSource)).all():
            typer.echo(f"{src.source_inode} {src.recent_name} @ {src.parent_dir} -> {len(src.rules)} rules")
            for r in src.rules:
                typer.echo(f"  {r.target_path} [{r.target_inode}]")


@rules.command("rm")
def rules_remove(source_dir: Path = typer.Argument(...), target_dir: Path = typer.Argument(...)) -> None:
    rid = os.stat(norm_path(source_dir)).st_ino
    tid = os.stat(norm_path(target_dir)).st_ino
    with get_session() as s:
        rule = s.get(Rule, {"source_inode": rid, "target_inode": tid})
        if rule is not None:
            s.delete(rule)
            s.commit()
            typer.echo("rule removed")
        else:
            typer.echo("no rule")


@rules.command("apply")
def rules_apply() -> None:
    with get_session() as s:
        for src in s.scalars(select(RuleSource)).all():
            source_path = Path(src.parent_dir) / src.recent_name
            for r in src.rules:
                parent = Path(r.target_path)
                parent.mkdir(parents=True, exist_ok=True)
                link = parent / str(src.source_inode)
                if link.exists() or link.is_symlink():
                    if link.is_dir() and not link.is_symlink():
                        shutil.rmtree(link)
                    else:
                        link.unlink()
                os.symlink(str(source_path), str(link), target_is_directory=True)
                typer.echo(str(link))
