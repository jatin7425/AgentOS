from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from api.v1 import router as v1_router
from config import get_env
from db.data_store import DataStore
from db.vector_store import create_vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    env = get_env()
    async with AsyncExitStack() as cleanup:
        app.state.data_store = DataStore(env.database_url)
        cleanup.push_async_callback(app.state.data_store.close)
        app.state.vector_store = create_vector_store(
            env.vector_store_backend, env.vector_db_url
        )
        cleanup.push_async_callback(app.state.vector_store.close)
        await app.state.data_store.check()
        await app.state.vector_store.check()
        yield


app = FastAPI(
    lifespan=lifespan,
    docs_url="/api/docs",
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.include_router(v1_router, prefix="/api")
