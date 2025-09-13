from __future__ import annotations
import os
import shutil
from pathlib import Path

import typer
from sqlalchemy import select
from zerolink.db import get_session, LinkDir, Rule, DEFAULT_DB

def norm_path(p: str | Path) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(str(p)))).resolve()

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("init")
def init_command() -> None:
    base = os.getenv("LOCALAPPDATA")
    db_path = Path(base) / "zerolink" / DEFAULT_DB
    if db_path.exists():
        if typer.confirm("Clear & re-initialize database?"):
            db_path.unlink()
            with get_session() as s:
                s.flush()
            typer.echo("Re-initialized global database")
        else:
            typer.echo(f"Database already exists: {db_path}")
            return
    else:
        with get_session() as s:
            s.flush()
        typer.echo("Initialized global database")


rules = typer.Typer(help="Manage directory linking rules")
app.add_typer(rules, name="rules")


# Import isolated link command and register it without creating a dependency back to this file
from .link_command import link_command as _isolated_link

app.command("link")(_isolated_link)

@rules.command("add")
def rules_add(src: Path = typer.Argument(...), dst: Path = typer.Argument(...)) -> None:
    src_p = norm_path(src)
    dst_p = norm_path(dst)
    lid = os.stat(dst_p).st_ino  # link location (dst)
    tid = os.stat(src_p).st_ino  # target (src)
    with get_session() as s:
        linkdir = s.get(LinkDir, lid)
        if linkdir is None:
            linkdir = LinkDir(link_inode=lid, recent_name=dst_p.name, parent_dir=str(dst_p.parent))
            s.add(linkdir)
        else:
            linkdir.recent_name = dst_p.name
            linkdir.parent_dir = str(dst_p.parent)

        existing = s.execute(
            select(Rule).where(Rule.link_inode == lid, Rule.target_inode == tid)
        ).scalar_one_or_none()
        if existing is None:
            rule = Rule(link_inode=lid, target_inode=tid, target_name=src_p.name, target_path=str(src_p))
            s.add(rule)
            s.flush()
            rule_id = rule.id
        else:
            existing.target_name = src_p.name
            existing.target_path = str(src_p)
            rule_id = existing.id
        s.commit()
    typer.echo(f"rule {rule_id}: dst {dst_p} <= src {src_p}")


# Note: listing is integrated into `rules apply` now.


@rules.command("rm")
def rules_remove(id: int = typer.Argument(...)) -> None:
    with get_session() as s:
        rule = s.get(Rule, id)
        if rule is not None:
            s.delete(rule)
            s.commit()
            typer.echo(f"Removed rule {id}")
        else:
            typer.echo(f"No rule {id}")


@rules.command("apply")
def rules_apply() -> None:
    with get_session() as s:
        # Build a straightforward plan: always add (replace if exists)
        plan: list[dict] = []
        for linkdir in s.scalars(select(LinkDir)).all():
            dst_path = Path(linkdir.parent_dir) / linkdir.recent_name
            for r in linkdir.rules:
                link_path = dst_path
                src_path = Path(r.target_path)
                # Count items that will be removed at dst before linking
                if link_path.is_symlink() or link_path.is_file():
                    del_items = 1
                elif link_path.is_dir():
                    del_items = 1 + sum(1 for _ in link_path.rglob("*"))
                else:
                    del_items = 0
                plan.append(
                    {
                        "rule_id": r.id,
                        "dst": str(link_path),
                        "src": str(src_path),
                        "del_items": del_items,
                    }
                )

        # Summaries
        adds = len(plan)
        del_items = sum(e["del_items"] for e in plan)

        # Preview (list rules and what will be deleted)
        typer.echo("Planned changes:")
        for e in plan:
            rid, dst, src, dels = e["rule_id"], e["dst"], e["src"], e["del_items"]
            typer.echo(f"  [{rid}] {dst} <= {src} (delete {dels} items)")
        typer.echo(f"add: {adds}")
        typer.echo(f"delete: {del_items}")

        if not typer.confirm(
            f"Apply changes? add={adds} (delete items={del_items})"
        ):
            typer.echo("No changes applied.")
            return

        # Apply
        for e in plan:
            dst_p = Path(e["dst"])
            src_p2 = Path(e["src"])
            typer.echo(f"apply: {dst_p} <= {src_p2}")
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            if dst_p.exists() or dst_p.is_symlink():
                if dst_p.is_dir() and not dst_p.is_symlink():
                    shutil.rmtree(dst_p)
                else:
                    dst_p.unlink()
            os.symlink(str(src_p2), str(dst_p), target_is_directory=True)

        # Final summary
        typer.echo(f"Applied {len(plan)} rule(s)")
