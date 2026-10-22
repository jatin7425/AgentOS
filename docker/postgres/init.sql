-- Safe to rerun against an existing volume; CREATE DATABASE cannot run in a transaction.
SELECT 'CREATE DATABASE agentos OWNER agentos'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agentos')
\gexec

SELECT 'CREATE DATABASE agentos_vectors OWNER agentos'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agentos_vectors')
\gexec

\connect agentos_vectors
CREATE EXTENSION IF NOT EXISTS vector;
