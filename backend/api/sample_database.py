"""Built-in AdventureWorks LT sample analytics SQLite DB."""

from __future__ import annotations

import shutil
import sqlite3
import urllib.request
from pathlib import Path

from django.conf import settings

SAMPLE_FILENAME = "helix-sample.sqlite"
SOURCE_FILENAME = "adventureworks-lt.source.sqlite"
SAMPLE_VERSION = 2
META_TABLE = "_helix_sample_meta"

# Logical schema name for Docs / DB Explorer (AdventureWorks LT).
SAMPLE_SCHEMA = "SalesLT"

# Community AdventureWorks LT port for SQLite (~2.8 MB).
ADVENTUREWORKS_SQLITE_URL = (
    "https://raw.githubusercontent.com/martinandersen3d/"
    "AdventureWorks-for-SQLite/master/AdventureWorks-sqlite.db"
)

# Tables agents may query (exclude BuildVersion / ErrorLog / sqlite internals).
SAMPLE_TABLES = (
    "Address",
    "Customer",
    "CustomerAddress",
    "Product",
    "ProductCategory",
    "ProductDescription",
    "ProductModel",
    "ProductModelProductDescription",
    "SalesOrderDetail",
    "SalesOrderHeader",
)


def sample_data_dir() -> Path:
    return Path(settings.BASE_DIR) / "data"


def default_sample_db_path() -> Path:
    return sample_data_dir() / SAMPLE_FILENAME


def source_db_path() -> Path:
    return sample_data_dir() / SOURCE_FILENAME


def is_sample_db_path(path: str | Path | None) -> bool:
    if path is None:
        return True
    text = str(path).strip()
    if not text:
        return True
    name = Path(text).name.lower()
    return name in {
        SAMPLE_FILENAME.lower(),
        SOURCE_FILENAME.lower(),
        "sample",
        "helix-sample",
        "sample.sqlite",
        "sample.db",
        "adventureworks-lt.sqlite",
        "adventureworks.sqlite",
    }


def resolve_sqlite_path(raw: str | None = None) -> Path:
    """Resolve configured sqlite path; blank/sample tokens → built-in sample file."""
    text = (raw or "").strip()
    if not text or is_sample_db_path(text):
        return default_sample_db_path()
    path = Path(text)
    if not path.is_absolute():
        path = Path(settings.BASE_DIR) / path
    return path


def _current_version(conn: sqlite3.Connection) -> int | None:
    try:
        row = conn.execute(
            f"SELECT version FROM {META_TABLE} ORDER BY version DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def _table_count(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
          AND name != ?
        """,
        (META_TABLE,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _has_adventureworks_tables(conn: sqlite3.Connection) -> bool:
    names = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    required = {"Customer", "Product", "SalesOrderHeader", "SalesOrderDetail"}
    return required.issubset(names)


def download_adventureworks_source(*, force: bool = False) -> Path:
    """Download AdventureWorks LT SQLite into backend/data if missing."""
    target = source_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 100_000 and not force:
        return target

    tmp = target.with_suffix(".download")
    try:
        urllib.request.urlretrieve(ADVENTUREWORKS_SQLITE_URL, tmp)  # noqa: S310
        if not tmp.exists() or tmp.stat().st_size < 100_000:
            raise RuntimeError("AdventureWorks download was empty or too small")
        with sqlite3.connect(str(tmp)) as conn:
            if not _has_adventureworks_tables(conn):
                raise RuntimeError(
                    "Downloaded file is not a recognizable AdventureWorks LT database"
                )
        if target.exists():
            target.unlink()
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return target


def _stamp_meta(conn: sqlite3.Connection) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {META_TABLE}")
    conn.execute(
        f"""
        CREATE TABLE {META_TABLE} (
            version INTEGER NOT NULL,
            note TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"INSERT INTO {META_TABLE} (version, note) VALUES (?, ?)",
        (
            SAMPLE_VERSION,
            "AdventureWorks LT (SQLite port) - Helix built-in sample",
        ),
    )


def ensure_sample_database(path: Path | None = None, *, force: bool = False) -> Path:
    """
    Ensure the sample SQLite file is AdventureWorks LT.

    Downloads the community AdventureWorks LT SQLite DB when needed, then
    copies it to the configured sample path and stamps a Helix meta version.
    """
    target = Path(path) if path is not None else default_sample_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    needs_seed = force or not target.exists()
    if not needs_seed:
        with sqlite3.connect(str(target)) as conn:
            version = _current_version(conn)
            needs_seed = (
                version != SAMPLE_VERSION
                or _table_count(conn) == 0
                or not _has_adventureworks_tables(conn)
            )

    if needs_seed:
        source = download_adventureworks_source(force=force)
        building = target.with_suffix(target.suffix + ".building")
        if building.exists():
            building.unlink()
        shutil.copy2(source, building)
        with sqlite3.connect(str(building)) as conn:
            _stamp_meta(conn)
            conn.commit()
        try:
            if target.exists():
                target.unlink()
            building.replace(target)
        except PermissionError:
            # Windows: API process may still hold the old sample open.
            # Leave the built file beside the target for the next restart.
            raise PermissionError(
                f"Could not replace {target.name} while it is in use. "
                f"Stop the API, delete {target.name} if needed, then restart "
                f"(built sample is at {building.name})."
            ) from None

    return target


def ensure_sqlite_file(path: Path | None = None) -> Path:
    """Create/seed the sample DB when `path` is the built-in sample file."""
    target = Path(path) if path is not None else default_sample_db_path()
    if (
        is_sample_db_path(target)
        or target.resolve() == default_sample_db_path().resolve()
    ):
        return ensure_sample_database(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def ensure_configured_sample_if_needed() -> Path | None:
    """If the user did not provide a warehouse, persist sqlite sample and seed it."""
    from .config_loader import (
        DEFAULT_DATABASE,
        get_database_engine,
        get_database_settings,
        is_user_provided_database,
        load_config,
        save_config,
    )

    data = load_config()
    raw = data.get("database") if isinstance(data.get("database"), dict) else {}
    from .db_dialects.base import normalize_engine

    engine = normalize_engine(raw.get("engine") if isinstance(raw, dict) else None)
    if engine == "sqlite" and not is_user_provided_database(raw):
        data["database"] = {**DEFAULT_DATABASE}
        save_config(data)

    if get_database_engine() != "sqlite":
        return None
    db = get_database_settings()
    path = resolve_sqlite_path(db.get("name") or db.get("path") or "")
    if not is_sample_db_path(path) and path.resolve() != default_sample_db_path().resolve():
        return None
    try:
        return ensure_sample_database(path)
    except PermissionError as exc:
        # Avoid crashing Django startup when an old sample file is locked.
        import logging

        logging.getLogger(__name__).warning("%s", exc)
        return None
