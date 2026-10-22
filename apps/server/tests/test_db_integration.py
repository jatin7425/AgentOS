"""Run against Compose databases: docker compose exec -T server python < apps/server/tests/test_db_integration.py"""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, literal, select, text

from api.app import lifespan
from db.data_store import DataStore, get_session
from db.vector_store import PgVectorStore


class DatabaseIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_isolation_transactions_and_vector_types(self):
        app = FastAPI()
        async with lifespan(app):
            data = app.state.data_store
            vector = app.state.vector_store
            self.assertIsNot(data.engine, vector.db.engine)
            for store, name in [(data, 'agentos'), (vector.db, 'agentos_vectors')]:
                async with store.Session.begin() as session:
                    result = await session.execute(text('SELECT current_database()'))
                    self.assertEqual(result.scalar_one(), name)

            with self.assertRaisesRegex(RuntimeError, 'rollback'):
                async with data.Session.begin() as session:
                    await session.execute(text('CREATE TABLE sqlalchemy_rollback_check (id integer)'))
                    raise RuntimeError('rollback')
            async with data.Session.begin() as session:
                result = await session.execute(text("SELECT to_regclass('sqlalchemy_rollback_check')"))
                self.assertIsNone(result.scalar_one())

            async with vector.db.Session.begin() as session:
                embedding = cast(literal([1.0, 2.0, 3.0], type_=Vector(3)), Vector(3))
                result = await session.execute(select(embedding.l2_distance([1.0, 2.0, 4.0])))
                self.assertEqual(result.scalar_one(), 1.0)
                result = await session.execute(select(embedding))
                self.assertEqual(list(result.scalar_one()), [1.0, 2.0, 3.0])

            # The request dependency yields a SQLAlchemy session and closes it.
            request = type('Request', (), {'app': app})()
            async for session in get_session(request):
                self.assertEqual((await session.execute(text('SELECT 42'))).scalar_one(), 42)

        self.assertEqual(data.engine.pool.checkedout(), 0)
        self.assertEqual(vector.db.engine.pool.checkedout(), 0)

    async def test_startup_failure_disposes_both_stores(self):
        data = AsyncMock(spec=DataStore)
        vector = AsyncMock(spec=PgVectorStore)
        vector.check.side_effect = RuntimeError('vector unavailable')
        with patch('api.app.DataStore', return_value=data), patch('api.app.create_vector_store', return_value=vector):
            with self.assertRaisesRegex(RuntimeError, 'vector unavailable'):
                async with lifespan(FastAPI()):
                    self.fail('Startup should fail')
        data.close.assert_awaited_once()
        vector.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
