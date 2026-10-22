"""Read backend configuration from Docker's environment; no .env file needed."""

import os
from dataclasses import dataclass, field


def _required(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ValueError(f"Required environment variable {name} is missing or empty")
    return value


@dataclass(frozen=True)
class Env:
    database_url: str = field(repr=False)
    vector_db_url: str = field(repr=False)
    vector_store_backend: str


def get_env() -> Env:
    """Load one configuration snapshot during application startup."""
    return Env(
        database_url=_required("DATABASE_URL"),
        vector_db_url=_required("VECTOR_DB_URL"),
        vector_store_backend=_required("VECTOR_STORE_BACKEND"),
    )
