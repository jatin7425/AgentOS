import os
import unittest
from unittest.mock import patch

from config.env import get_env


class EnvironmentTests(unittest.TestCase):
    values = {
        "DATABASE_URL": "postgresql://user:secret@db/data",
        "VECTOR_DB_URL": "postgresql://user:secret@db/vectors",
        "VECTOR_STORE_BACKEND": "pgvector",
    }

    def test_reads_separate_urls(self):
        with patch.dict(os.environ, self.values, clear=True):
            env = get_env()
        self.assertEqual(env.database_url, self.values['DATABASE_URL'])
        self.assertEqual(env.vector_db_url, self.values['VECTOR_DB_URL'])
        self.assertEqual(env.vector_store_backend, 'pgvector')
        self.assertNotIn('secret', repr(env))

    def test_rejects_each_missing_or_blank_variable(self):
        for name in self.values:
            for value in (None, '', '   '):
                with self.subTest(name=name, value=value):
                    values = dict(self.values)
                    if value is None:
                        del values[name]
                    else:
                        values[name] = value
                    with patch.dict(os.environ, values, clear=True):
                        with self.assertRaisesRegex(ValueError, name):
                            get_env()


if __name__ == '__main__':
    unittest.main()
