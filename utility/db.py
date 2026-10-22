import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _url(user: str, password: str) -> URL:
    return URL.create(
        drivername="postgresql+psycopg",
        username=user,
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "shop"),
    )


def _make_engine(url: URL, read_only: bool = False) -> Engine:
    connect_args = {"connect_timeout": 5}
    if read_only:
        connect_args["options"] = (
            "-c default_transaction_read_only=on -c statement_timeout=10000"
        )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args,
    )


@lru_cache
def get_engine() -> Engine:
    """Read-write engine (app writes, seeding)."""
    return _make_engine(_url(os.environ["DB_USER"], os.environ["DB_PASSWORD"]))


@lru_cache
def get_ro_engine() -> Engine:
    """Read-only engine (agent's SQL tool)."""
    return _make_engine(
        _url(os.environ["DB_RO_USER"], os.environ["DB_RO_PASSWORD"]), read_only=True
    )


@contextmanager
def connection(read_only: bool = True):
    engine = get_ro_engine() if read_only else get_engine()
    with engine.connect() as conn:
        yield conn


@contextmanager
def transaction():
    """Commits on success, rolls back on error."""
    with get_engine().begin() as conn:
        yield conn


def fetch_all(query: str, params: dict | None = None, read_only: bool = True) -> list[dict]:
    with connection(read_only) as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]


def health_check() -> dict:
    status = {}
    for name, engine in [("rw", get_engine()), ("ro", get_ro_engine())]:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status[name] = "ok"
        except Exception as e:
            status[name] = f"error: {e}"
    return status


if __name__ == "__main__":
    print(health_check())
    print(fetch_all("SELECT * FROM products LIMIT 3"))
