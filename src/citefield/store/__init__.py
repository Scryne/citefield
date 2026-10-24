"""Persistence: an SQLite file in the data directory, migrated on start."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

MIGRATIONS = Path(__file__).parent / "migrations"


def engine_for(data_dir: Path) -> Engine:
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{(data_dir / 'citefield.db').as_posix()}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _pragmas(conn, _record):  # type: ignore[no-untyped-def]
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")  # the worker writes while the API reads
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


def _config(engine: Engine) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", MIGRATIONS.as_posix())
    cfg.attributes["engine"] = engine
    return cfg


def migrate(engine: Engine) -> None:
    cfg = _config(engine)
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


class Store:
    def __init__(self, data_dir: Path) -> None:
        self.dir = data_dir
        self.engine = engine_for(data_dir)
        migrate(self.engine)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._sessions() as s, s.begin():
            yield s
