from __future__ import annotations

from pathlib import Path
import os

from sqlalchemy import (
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    select,
    DateTime,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


DEFAULT_DB = "zerolinks.sqlite3"


class Base(DeclarativeBase):
    pass


class UserSetting(Base):
    __tablename__ = "user_settings"

    # Store settings as simple KEY=VALUE rows, key is the primary key
    name: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class UserListItem(Base):
    __tablename__ = "user_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("key", "value", name="uq_user_list_key_value"),
    )


def get_session() -> Session:
    base = os.getenv("LOCALAPPDATA")
    db_path = Path(base) / "zerolink" / DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    return Session(engine, autoflush=False, autocommit=False)


def init_db() -> Path:
    """Ensure the database directory and tables exist. Returns DB path."""
    base = os.getenv("LOCALAPPDATA")
    db_path = Path(base) / "zerolink" / DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    # Initialize default user settings if missing
    try:
        if get_user_setting("max_src_history") is None:
            set_user_setting("max_src_history", "100")
    except Exception:
        # Don't block init if settings fail; user can re-run later
        pass
    return db_path


def set_user_setting(name: str, value: str) -> None:
    """Create or update a user setting (KEY=VALUE)."""
    with get_session() as session:
        setting = session.get(UserSetting, name)
        if setting is None:
            setting = UserSetting(name=name, value=value)
            session.add(setting)
        else:
            setting.value = value
        session.commit()


def get_user_setting(name: str) -> str | None:
    """Return the value for a setting key, or None if unset."""
    with get_session() as session:
        setting = session.get(UserSetting, name)
        return setting.value if setting else None


def remove_user_setting(name: str) -> bool:
    """Remove a setting by key. Returns True if it existed and was removed."""
    with get_session() as session:
        setting = session.get(UserSetting, name)
        if not setting:
            return False
        session.delete(setting)
        session.commit()
        return True


def list_user_settings() -> dict[str, str]:
    """Return all user settings as a dict of key -> value."""
    with get_session() as session:
        rows = session.scalars(select(UserSetting))
        return {r.name: r.value for r in rows}


# -------- Generic user lists (history) --------

def add_user_list_item(key: str, value: str, max_items: int = 100) -> None:
    """Add or bump an item in a named user list.

    - Ensures uniqueness per (key, value)
    - Maintains MRU ordering via `last_used_at`
    - Trims list to `max_items` by removing oldest items
    """
    with get_session() as session:
        # Try to find existing
        existing = session.execute(
            select(UserListItem).where(
                UserListItem.key == key, UserListItem.value == value
            )
        ).scalar_one_or_none()

        if existing:
            # Bump last_used_at via touching the row
            existing.value = value  # no-op change; onupdate will set last_used_at
        else:
            session.add(UserListItem(key=key, value=value))

        session.flush()

        # Enforce max size: keep most recently used first
        if max_items is not None and max_items > 0:
            rows = (
                session.execute(
                    select(UserListItem.id)
                    .where(UserListItem.key == key)
                    .order_by(
                        UserListItem.last_used_at.desc(),
                        UserListItem.created_at.desc(),
                    )
                    .offset(max_items)
                )
                .scalars()
                .all()
            )
            if rows:
                session.query(UserListItem).filter(UserListItem.id.in_(rows)).delete(
                    synchronize_session=False
                )
        session.commit()


def get_user_list(key: str, limit: int | None = None) -> list[str]:
    """Return the values for a named user list in MRU order."""
    with get_session() as session:
        q = (
            select(UserListItem.value)
            .where(UserListItem.key == key)
            .order_by(UserListItem.last_used_at.desc(), UserListItem.created_at.desc())
        )
        if limit is not None and limit > 0:
            q = q.limit(limit)
        return list(session.scalars(q))


def remove_user_list_item(key: str, value: str) -> bool:
    """Remove a specific item from a named user list."""
    with get_session() as session:
        row = session.execute(
            select(UserListItem).where(
                UserListItem.key == key, UserListItem.value == value
            )
        ).scalar_one_or_none()
        if not row:
            return False
        session.delete(row)
        session.commit()
        return True


def clear_user_list(key: str) -> int:
    """Clear all items for a named user list. Returns number deleted."""
    with get_session() as session:
        deleted = session.query(UserListItem).filter(UserListItem.key == key).delete(
            synchronize_session=False
        )
        session.commit()
        return int(deleted or 0)


__all__ = [
    "DEFAULT_DB",
    "Base",
    "UserSetting",
    "UserListItem",
    "get_session",
    "init_db",
    "set_user_setting",
    "get_user_setting",
    "remove_user_setting",
    "list_user_settings",
    "add_user_list_item",
    "get_user_list",
    "remove_user_list_item",
    "clear_user_list",
]
