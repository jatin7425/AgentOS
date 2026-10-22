from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi import Request


class DataStore:
    def __init__(self, url: str):
        # Tell SQLAlchemy to use the async "psycopg" driver
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        self.engine = create_async_engine(url, pool_pre_ping=True)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def check(self):
        async with self.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def close(self):
        await self.engine.dispose()


async def get_session(request: Request):
    session = request.app.state.data_store.Session()
    try:
        yield session
        await session.commit()      # success → save
    except Exception:
        await session.rollback()    # error → undo
        raise                       # pass the error on
    finally:
        await session.close()       # always → close