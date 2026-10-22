import os
import uuid
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain.embeddings import init_embeddings
from langchain_core.documents import Document
from langchain_postgres import PGEngine, PGVectorStore
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TABLE = os.getenv("VECTOR_TABLE", "documents")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


def _url() -> str:
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.environ["VECTOR_DB_USER"],
        password=os.environ["VECTOR_DB_PASSWORD"],
        host=os.getenv("VECTOR_DB_HOST", "localhost"),
        port=int(os.getenv("VECTOR_DB_PORT", "5432")),
        database=os.getenv("VECTOR_DB_NAME", "vectors"),
    ).render_as_string(hide_password=False)


@lru_cache
def get_embeddings():
    return init_embeddings(os.getenv("EMBEDDING_MODEL", "openai:text-embedding-3-small"))


@lru_cache
def get_pg_engine() -> PGEngine:
    return PGEngine.from_connection_string(url=_url())


def ensure_table() -> None:
    """Create the vector table once. Safe to call every startup."""
    if TABLE in inspect(create_engine(_url())).get_table_names():
        return
    get_pg_engine().init_vectorstore_table(table_name=TABLE, vector_size=EMBEDDING_DIM)


@lru_cache
def get_vector_store() -> PGVectorStore:
    ensure_table()
    return PGVectorStore.create_sync(
        engine=get_pg_engine(),
        table_name=TABLE,
        embedding_service=get_embeddings(),
    )


# ---------- helpers ----------

def add_texts(texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
    ids = [str(uuid.uuid4()) for _ in texts]
    docs = [
        Document(id=i, page_content=t, metadata=(metadatas[n] if metadatas else {}))
        for n, (i, t) in enumerate(zip(ids, texts))
    ]
    get_vector_store().add_documents(docs)
    return ids


def search(query: str, k: int = 4, filter: dict | None = None) -> list[Document]:
    return get_vector_store().similarity_search(query, k=k, filter=filter)


def delete(ids: list[str]) -> None:
    get_vector_store().delete(ids)


def get_retriever(k: int = 4):
    return get_vector_store().as_retriever(search_kwargs={"k": k})


if __name__ == "__main__":
    ids = add_texts(
        ["Returns are accepted within 7 days of delivery.",
         "Shipping is free on orders above Rs 999."],
        metadatas=[{"source": "policy.md"}, {"source": "shipping.md"}],
    )
    for d in search("how many days do I have to return?", k=1):
        print(d.metadata, d.page_content)
    delete(ids)
