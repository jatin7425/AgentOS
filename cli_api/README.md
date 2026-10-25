# CLI Learning API

A small FastAPI gateway in one folder. Follows OmniRoute's single OpenAI-compatible
endpoint and provider routing approach, using subprocesses for local CLI execution.
This is a learning gateway, not a full OmniRoute implementation.

## Start with Docker Compose

From the repository root:

```bash
./setup.sh
# Or, after setup:
docker compose up -d --build cli-api
docker compose logs -f cli-api
```

The service uses the **root `.env`** through Compose `env_file`. `setup.sh` adds
`CLI_API_BASE_URL=http://localhost:8088/v1` if absent and preserves custom URLs.
Change `CLI_API_PORT` before setup to use another host port. When changing it later,
update `CLI_API_BASE_URL` too. From another Compose service use
`http://cli-api:8088/v1` instead of localhost.

The image installs Claude Code and Codex. Compose also mounts the host's
`~/.local/bin/agy` executable and `~/.gemini/antigravity-cli` auth directory
read-only into the container, so Antigravity can be used without installing it
in the image. Override `CLI_API_ANTIGRAVITY_BINARY` and
`CLI_API_ANTIGRAVITY_AUTH_DIR` in root `.env` if those paths differ. Detection
checks the container's PATH. Existing Linux logins in `~/.claude/.credentials.json`,
`~/.codex/auth.json`, and Antigravity's OAuth token are copied at startup from
read-only mounts into the container's writable home. The host's other configuration,
hooks, MCP servers, and history are not copied. Compose creates missing host auth
directories as empty directories; login on the host first, then restart the service
after renewing credentials.
Alternatively pass `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` through the root `.env`.
Keychain-only login is not copied. Override `CLI_CLAUDE_AUTH_DIR` /
`CLI_CODEX_AUTH_DIR` to use different host directories.

API docs: http://localhost:8088/docs

```bash
curl http://localhost:8088/providers
curl http://localhost:8088/v1/models
curl http://localhost:8088/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"Explain Python generators briefly."}]}'
```

If `CLI_API_KEY` is set in the root `.env`, add `Authorization: Bearer YOUR_KEY`.
The published Docker port is bound to localhost.

## Models and routing

| Model | Route |
| --- | --- |
| `claude` or `cc` | Claude Code default model |
| `claude/sonnet` or `cc/sonnet` | Explicit Claude model |
| `codex` or `cx` | Codex default model |
| `codex/model-name` or `cx/model-name` | Explicit Codex model |
| `antigravity` or `ag` | Antigravity `agy` print mode, or configured wrapper |
| `auto` | Try `CLI_API_FALLBACK` in order |

Fallback defaults to `claude,codex,antigravity`; unavailable CLIs and execution errors
advance to the next candidate. Explicit provider requests never silently switch.
Responses report the selected model. Installed does not mean authenticated:
`/providers` reports executable detection, and a completion verifies actual access.

The Antigravity integration uses `agy` non-interactive print mode with sandboxing
enabled. Compose makes the host executable available inside the container; when
running `cli_api` directly on the host, it detects `agy` on the host PATH instead.
Alternatively, stop the Compose API first to free its port and run the API locally:

```bash
docker compose stop cli-api
.venv/bin/python -m uvicorn cli_api.app:app --host 127.0.0.1 --port 8088
```

For a custom integration, set `CLI_API_ANTIGRAVITY_COMMAND` in root `.env` to a
JSON argv array. The command must read the prompt from stdin and write only the
final answer to stdout, and must exist in the environment where the API runs.
At least one provider CLI must be installed and available for completions; the
other providers are optional. No GUI scraping, credential extraction, or private
API integration is included.

## LangChain

```bash
.venv/bin/python -m cli_api.example_langchain
```

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()  # root .env when running from the repository
llm = ChatOpenAI(
    base_url=os.environ['CLI_API_BASE_URL'],
    api_key=os.getenv('CLI_API_KEY') or 'local-learning',
    model='auto',
    timeout=600,
    max_retries=0,
    use_responses_api=False,
)
print(llm.invoke('Explain list comprehensions.').content)
```

Each request sends the entire supplied message history as a JSON transcript in one
CLI prompt. Role priority is prompt-based, not native provider message separation.
Text and text-part arrays work. `stream=True` provides buffered SSE: the CLI finishes
first, then the answer and `[DONE]` are emitted. This is not live token streaming.
Usage is `null` because token counts are not normalized. Tools/tool calling,
multimodal input, structured output, temperature, and token limits return explicit
400 errors. Consequently LangChain chat/prompt chains work; `bind_tools`, agents
requiring tool calls, embeddings, and the Responses API are not implemented.

Execution uses stdin and an argument array with no shell. Claude built-in tools
and configured MCP tools are disabled; Codex runs with its read-only sandbox.
Both run from temporary directories, with no repository mounted into Docker.
CLI sandbox support depends on the container runtime; failures return provider
errors rather than bypassing sandbox permissions. Requests have a per-attempt
180-second timeout and concurrency of two by default (`CLI_API_TIMEOUT`,
`CLI_API_CONCURRENCY`). An auto fallback can take several attempt timeouts, so the
example uses a longer client timeout. No model call retries are hidden.

## Verify

```bash
.venv/bin/python -m unittest cli_api.test_app -v
docker compose config --quiet
```

Tests use local fake subprocesses and an in-process HTTP client, including real
LangChain invocation and streaming. They do not make paid model requests.

References: [OmniRoute CLI architecture](https://omniroute.hagicode.com/en-US/reference/cli-tools/)
and [Codex noninteractive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
