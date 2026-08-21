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

TIER_SMALL = "small"
TIER_MEDIUM = "medium"
TIER_BIG = "big"
TIER_FILENAMES = {
    TIER_SMALL: "helix-sample-small.sqlite",
    TIER_MEDIUM: "helix-sample-medium.sqlite",
    TIER_BIG: "helix-sample-big.sqlite",
}
# Approximate expected sizes for UI labels when file is missing.
TIER_SIZE_HINTS = {
    TIER_SMALL: 1_200_000,
    TIER_MEDIUM: 2_800_000,
    TIER_BIG: 55_000_000,
}
TIER_LABELS = {
    TIER_SMALL: "Small",
    TIER_MEDIUM: "Medium",
    TIER_BIG: "Big",
}
SMALL_ROW_CAPS = {
    "SalesOrderDetail": 200,
    "SalesOrderHeader": 80,
    "Customer": 100,
    "Product": 100,
    "Address": 100,
    "CustomerAddress": 100,
    "ProductCategory": 50,
    "ProductDescription": 100,
    "ProductModel": 50,
    "ProductModelProductDescription": 100,
}

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
        *(n.lower() for n in TIER_FILENAMES.values()),
    }


def resolve_sqlite_path(raw: str | None = None) -> Path:
    """Resolve configured sqlite path; blank/legacy sample tokens → built-in sample file."""
    text = (raw or "").strip()
    if not text:
        return default_sample_db_path()
    name = Path(text).name.lower()
    # Explicit AdventureWorks size tiers keep their own filenames.
    for filename in TIER_FILENAMES.values():
        if name == filename.lower():
            path = Path(text)
            if not path.is_absolute():
                path = sample_data_dir() / filename
            return path
    if is_sample_db_path(text):
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


def format_size_label(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    if size_bytes >= 1_000:
        return f"{size_bytes / 1_000:.0f} KB"
    return f"{size_bytes} B"


def tier_path(tier_id: str) -> Path:
    name = TIER_FILENAMES.get(tier_id)
    if not name:
        raise KeyError(f"Unknown sample tier: {tier_id}")
    return sample_data_dir() / name


def list_sample_tiers() -> list[dict]:
    tiers: list[dict] = []
    for tier_id in (TIER_SMALL, TIER_MEDIUM, TIER_BIG):
        path = tier_path(tier_id)
        exists = path.exists() and path.stat().st_size > 10_000
        size_bytes = path.stat().st_size if exists else TIER_SIZE_HINTS[tier_id]
        tiers.append(
            {
                "id": tier_id,
                "label": TIER_LABELS[tier_id],
                "filename": TIER_FILENAMES[tier_id],
                "exists": exists,
                "size_bytes": size_bytes,
                "size_label": format_size_label(size_bytes),
                "size_hint": not exists,
            }
        )
    return tiers


def _truncate_table(conn: sqlite3.Connection, table: str, limit: int) -> None:
    if limit <= 0:
        return
    try:
        conn.execute(
            f'DELETE FROM "{table}" WHERE rowid NOT IN '
            f'(SELECT rowid FROM "{table}" LIMIT ?)',
            (limit,),
        )
    except sqlite3.Error:
        pass


def _build_small_from_medium(medium: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    building = target.with_suffix(target.suffix + ".building")
    if building.exists():
        building.unlink()
    shutil.copy2(medium, building)
    with sqlite3.connect(str(building)) as conn:
        for table, cap in SMALL_ROW_CAPS.items():
            _truncate_table(conn, table, cap)
        _stamp_meta(conn)
        conn.commit()
        try:
            conn.execute("VACUUM")
        except sqlite3.Error:
            pass
        conn.commit()
    if target.exists():
        target.unlink()
    building.replace(target)
    return target


def _expand_table_rows(conn: sqlite3.Connection, table: str, copies: int) -> None:
    if copies < 1:
        return
    try:
        info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        cols = [row[1] for row in info]
        if not cols:
            return
        pk_cols = {row[1] for row in info if row[5]}
        insert_cols = [c for c in cols if c not in pk_cols] or cols
        col_sql = ", ".join(f'"{c}"' for c in insert_cols)
        for _ in range(copies):
            conn.execute(
                f'INSERT INTO "{table}" ({col_sql}) SELECT {col_sql} FROM "{table}"'
            )
    except sqlite3.Error:
        pass


def _build_big_from_medium(
    medium: Path, target: Path, *, min_bytes: int = 40_000_000
) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    building = target.with_suffix(target.suffix + ".building")
    if building.exists():
        building.unlink()
    shutil.copy2(medium, building)
    with sqlite3.connect(str(building)) as conn:
        for _ in range(8):
            building_size = building.stat().st_size if building.exists() else 0
            if building_size >= min_bytes:
                break
            _expand_table_rows(conn, "SalesOrderDetail", 1)
            _expand_table_rows(conn, "SalesOrderHeader", 1)
            conn.commit()
        _stamp_meta(conn)
        conn.commit()
    if target.exists():
        target.unlink()
    building.replace(target)
    return target


def ensure_sample_tier(tier_id: str, *, force: bool = False) -> dict:
    if tier_id not in TIER_FILENAMES:
        raise KeyError(f"Unknown sample tier: {tier_id}")
    target = tier_path(tier_id)
    if target.exists() and target.stat().st_size > 10_000 and not force:
        return {
            "id": tier_id,
            "label": TIER_LABELS[tier_id],
            "filename": TIER_FILENAMES[tier_id],
            "exists": True,
            "size_bytes": target.stat().st_size,
            "size_label": format_size_label(target.stat().st_size),
            "path": str(target),
        }

    medium = tier_path(TIER_MEDIUM)
    ensure_sample_database(medium, force=force)
    legacy = default_sample_db_path()
    if not legacy.exists() or force:
        try:
            shutil.copy2(medium, legacy)
        except OSError:
            pass

    if tier_id == TIER_MEDIUM:
        path = medium
    elif tier_id == TIER_SMALL:
        path = _build_small_from_medium(medium, target)
    else:
        path = _build_big_from_medium(medium, target)

    return {
        "id": tier_id,
        "label": TIER_LABELS[tier_id],
        "filename": TIER_FILENAMES[tier_id],
        "exists": True,
        "size_bytes": path.stat().st_size,
        "size_label": format_size_label(path.stat().st_size),
        "path": str(path),
    }
