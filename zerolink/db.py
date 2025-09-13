from __future__ import annotations

from pathlib import Path
import os

from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


DEFAULT_DB = "zerolinks.sqlite3"


class Base(DeclarativeBase):
    pass


class RuleSource(Base):
    __tablename__ = "rule_sources"

    source_inode: Mapped[int] = mapped_column(Integer, primary_key=True)
    recent_name: Mapped[str] = mapped_column(String, nullable=False)
    parent_dir: Mapped[str | None] = mapped_column(String, nullable=True)

    rules: Mapped[list["Rule"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Rule(Base):
    __tablename__ = "rules"

    source_inode: Mapped[int] = mapped_column(
        ForeignKey("rule_sources.source_inode", ondelete="CASCADE"), primary_key=True
    )
    target_inode: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_name: Mapped[str] = mapped_column(String, nullable=False)
    target_path: Mapped[str] = mapped_column(String, nullable=False)

    source: Mapped[RuleSource] = relationship(back_populates="rules")


def get_session() -> Session:
    base = os.getenv("LOCALAPPDATA")
    db_path = Path(base) / "zerolink" / DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    return Session(engine, autoflush=False, autocommit=False)


__all__ = [
    "DEFAULT_DB",
    "Base",
    "RuleSource",
    "Rule",
    "get_session",
]
