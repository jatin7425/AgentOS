from typing import Protocol
from sqlalchemy import text
from db.data_store import DataStore


class VectorStore(Protocol):
    async def check(self) -> None: ...
    async def close(self) -> None: ...


class PgVectorStore:
    def __init__(self, url: str):
        self.db = DataStore(url)

    async def check(self):
        async with self.db.engine.connect() as conn:
            await conn.execute(text("SELECT '[1,2,3]'::vector"))

    async def close(self):
        await self.db.close()


def create_vector_store(backend: str, url: str) -> VectorStore:
    if backend == "pgvector":
        return PgVectorStore(url)
    raise ValueError(f"Unknown vector backend: {backend}")