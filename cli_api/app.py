import asyncio
import hmac
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time
import uuid
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
app = FastAPI(title='CLI Learning API', version='1.0.0')
TIMEOUT = float(os.getenv('CLI_API_TIMEOUT', '180'))
OUTPUT_LIMIT = 2 * 1024 * 1024
slots = asyncio.Semaphore(int(os.getenv('CLI_API_CONCURRENCY', '2')))
ALIASES = {'cc': 'claude', 'cx': 'codex', 'ag': 'antigravity'}


class APIError(Exception):
    def __init__(self, status, message, code='invalid_request_error', param=None):
        self.status, self.message, self.code, self.param = status, message, code, param


@app.exception_handler(APIError)
async def api_error(request, exc):
    return JSONResponse(status_code=exc.status, content={'error': {
        'message': exc.message, 'type': exc.code, 'code': exc.code, 'param': exc.param}})


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return await api_error(request, APIError(400, 'Invalid request: ' + '; '.join(
        f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())))


async def authorize(request: Request):
    key = os.getenv('CLI_API_KEY')
    if key and not hmac.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + key):
        raise APIError(401, 'Invalid gateway API key.', 'authentication_error')


class TextPart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['text']
    text: str


class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['system', 'developer', 'user', 'assistant']
    content: str | list[TextPart]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: str = Field(min_length=1, max_length=200)
    messages: list[Message] = Field(min_length=1, max_length=200)
    stream: bool = False
    stream_options: dict | None = None
    n: Literal[1] = 1
    temperature: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    tools: list | None = None
    tool_choice: str | dict | None = None
    response_format: dict | None = None


def providers():
    result = {}
    for name in ('claude', 'codex', 'antigravity'):
        path = shutil.which(name)
        wrapper = os.getenv('CLI_API_ANTIGRAVITY_COMMAND') if name == 'antigravity' else None
        ready = bool(path) and name != 'antigravity'
        reason = None if ready else 'CLI not found on PATH.'
        if name == 'antigravity' and path:
            reason = 'Installed editor CLI has no headless stdout response mode; configure CLI_API_ANTIGRAVITY_COMMAND.'
        if wrapper:
            try:
                args = json.loads(wrapper)
                ready = bool(isinstance(args, list) and args and all(isinstance(a, str) for a in args)
                             and shutil.which(args[0]))
            except (ValueError, TypeError):
                ready = False
            reason = None if ready else 'Invalid or unavailable Antigravity wrapper command.'
        result[name] = {'installed': bool(path), 'path': path, 'available': ready, 'reason': reason}
    return result


def command(provider, model, workdir):
    path = providers()[provider]['path']
    if provider == 'claude':
        args = [path, '-p', '--output-format', 'json', '--tools', '',
                '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                '--no-session-persistence', '--disable-slash-commands']
    elif provider == 'codex':
        args = [path, 'exec', '--sandbox', 'read-only', '--skip-git-repo-check',
                '--ephemeral', '--color', 'never', '-o', str(workdir / 'answer.txt')]
    else:
        args = json.loads(os.environ['CLI_API_ANTIGRAVITY_COMMAND'])
    if model:
        if provider == 'antigravity':
            raise APIError(400, 'Antigravity wrapper uses its configured default model.')
        args += ['--model', model]
    if provider == 'codex':
        args += ['-']
    return args


async def terminate(proc):
    if proc.returncode is None:
        try:
            if os.name == 'posix':
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except ProcessLookupError:
            pass
    await proc.wait()


async def execute(provider, model, prompt):
    try:
        await asyncio.wait_for(slots.acquire(), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        raise APIError(429, 'Gateway busy; retry later.', 'rate_limit_error')
    try:
        with tempfile.TemporaryDirectory(prefix='cli-api-') as folder:
            workdir = Path(folder)
            args = command(provider, model, workdir)
            with (workdir / 'stdout').open('wb') as stdout, (workdir / 'stderr').open('wb') as stderr:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *args, stdin=asyncio.subprocess.PIPE, stdout=stdout, stderr=stderr,
                        cwd=folder, start_new_session=os.name == 'posix')
                except OSError:
                    raise APIError(503, 'Could not start CLI. Check installation and permissions.', 'provider_unavailable')
                try:
                    await asyncio.wait_for(proc.communicate(prompt.encode()), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    await terminate(proc)
                    raise APIError(504, 'CLI execution timed out.', 'provider_timeout')
                except BaseException:
                    await terminate(proc)
                    raise
            if proc.returncode:
                # Raw CLI diagnostics can contain local paths, credentials, or prompt text.
                raise APIError(502, f'{provider} exited with code {proc.returncode}. Check CLI login, model access and quota in your terminal.', 'provider_error')
            output = workdir / ('answer.txt' if provider == 'codex' else 'stdout')
            if not output.exists() or output.stat().st_size > OUTPUT_LIMIT:
                raise APIError(502, 'CLI response missing or exceeds 2 MiB.', 'provider_error')
            value = output.read_text(errors='replace').strip()
            if provider == 'claude':
                try:
                    data = json.loads(value)
                    if data.get('is_error'):
                        raise APIError(502, 'Claude reported an error. Check CLI authentication and quota.', 'provider_error')
                    value = data['result']
                except (ValueError, KeyError, TypeError, AttributeError):
                    raise APIError(502, 'Unexpected Claude JSON response.', 'provider_error')
            if not isinstance(value, str) or not value.strip():
                raise APIError(502, 'CLI returned an empty response.', 'provider_error')
            return value
    finally:
        slots.release()


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/providers', dependencies=[Depends(authorize)])
async def provider_status():
    return providers()


@app.get('/v1/models', dependencies=[Depends(authorize)])
async def models():
    return {'object': 'list', 'data': [
        {'id': name, 'object': 'model', 'created': 0, 'owned_by': 'local-cli'}
        for name, info in providers().items() if info['available']] + [
        {'id': 'auto', 'object': 'model', 'created': 0, 'owned_by': 'local-router'}]}


async def route(model_id, prompt):
    candidates = (os.getenv('CLI_API_FALLBACK', 'claude,codex,antigravity').split(',')
                  if model_id == 'auto' else [model_id])
    last_error = None
    for candidate in candidates:
        candidate = candidate.strip()
        provider, _, model = candidate.partition('/')
        provider = ALIASES.get(provider, provider)
        info = providers().get(provider)
        if info is None:
            last_error = APIError(404, f'Unknown model: {candidate}. Use claude, codex, auto, or provider/model-name.', 'model_not_found')
        elif not info['available']:
            last_error = APIError(503, info['reason'], 'provider_unavailable')
        else:
            try:
                return await execute(provider, model or None, prompt), candidate
            except APIError as exc:
                if exc.status < 500 and exc.status != 429:
                    raise
                last_error = exc
        if model_id != 'auto':
            raise last_error
    raise last_error or APIError(503, 'No providers configured.', 'provider_unavailable')


@app.post('/v1/chat/completions', dependencies=[Depends(authorize)])
async def chat(body: ChatRequest):
    for field in ('temperature', 'max_tokens', 'max_completion_tokens', 'tools', 'tool_choice', 'response_format'):
        if getattr(body, field) is not None:
            raise APIError(400, f'{field} is not supported by this text-only CLI gateway.', param=field)
    if body.stream_options and set(body.stream_options) - {'include_usage'}:
        raise APIError(400, 'Unsupported stream_options.')
    # CLIs accept a single prompt. Serialize the full conversation on every request.
    messages = [m.model_dump() for m in body.messages]
    prompt = ('Answer the final user message in the following JSON conversation. '
              'Respect system and developer instructions. Return only your answer.\n' +
              json.dumps(messages, ensure_ascii=False))
    if len(prompt.encode()) > 256 * 1024:
        raise APIError(413, 'Conversation exceeds 256 KiB.')
    answer, selected_model = await route(body.model, prompt)
    identity, created = 'chatcmpl-' + uuid.uuid4().hex, int(time.time())
    base = {'id': identity, 'created': created, 'model': selected_model}
    if not body.stream:
        return {**base, 'object': 'chat.completion', 'choices': [
            {'index': 0, 'message': {'role': 'assistant', 'content': answer}, 'finish_reason': 'stop'}],
            'usage': None}

    async def events():
        def event(delta, finish=None):
            return 'data: ' + json.dumps({**base, 'object': 'chat.completion.chunk', 'choices': [
                {'index': 0, 'delta': delta, 'finish_reason': finish}]}) + '\n\n'
        yield event({'role': 'assistant', 'content': ''})
        yield event({'content': answer})
        yield event({}, 'stop')
        if body.stream_options and body.stream_options.get('include_usage'):
            yield 'data: ' + json.dumps({**base, 'object': 'chat.completion.chunk', 'choices': [], 'usage': None}) + '\n\n'
        yield 'data: [DONE]\n\n'
    return StreamingResponse(events(), media_type='text/event-stream')
