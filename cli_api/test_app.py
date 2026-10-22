import asyncio
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from langchain_openai import ChatOpenAI

gateway = importlib.import_module('cli_api.app')


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.env = patch.dict(os.environ, {'CLI_API_KEY': ''})
        self.env.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url='http://test')
        self.payload = {'model': 'claude', 'messages': [{'role': 'user', 'content': 'hello'}]}

    async def asyncTearDown(self):
        await self.client.aclose()
        self.env.stop()

    async def test_completion_and_langchain(self):
        with patch.object(gateway, 'route', AsyncMock(return_value=('Hello!', 'claude'))):
            response = await self.client.post('/v1/chat/completions', json=self.payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['choices'][0]['message']['content'], 'Hello!')
            llm = ChatOpenAI(model='claude', api_key='local', base_url='http://test/v1',
                             http_async_client=self.client, max_retries=0, use_responses_api=False)
            self.assertEqual((await llm.ainvoke('hello')).content, 'Hello!')
            chunks = [chunk async for chunk in llm.astream('hello')]
            self.assertEqual(''.join(c.content for c in chunks), 'Hello!')

    async def test_auth_and_validation(self):
        with patch.dict(os.environ, {'CLI_API_KEY': 'secret'}):
            self.assertEqual((await self.client.get('/v1/models')).status_code, 401)
            self.assertEqual((await self.client.get('/v1/models', headers={'Authorization': 'Bearer secret'})).status_code, 200)
        response = await self.client.post('/v1/chat/completions', json={**self.payload, 'tools': []})
        self.assertEqual(response.status_code, 400)
        response = await self.client.post('/v1/chat/completions', json={**self.payload, 'messages': []})
        self.assertIn('error', response.json())
        self.assertEqual(response.status_code, 400)

    async def test_detection_and_fallback(self):
        with patch.object(gateway.shutil, 'which', return_value='/bin/fake'):
            self.assertFalse(gateway.providers()['antigravity']['available'])
            with patch.object(gateway, 'execute', AsyncMock(side_effect=[
                gateway.APIError(502, 'failed'), 'fallback answer'])) as execute:
                answer, model = await gateway.route('auto', 'hello')
                self.assertEqual((answer, model), ('fallback answer', 'codex'))
                self.assertEqual(execute.await_count, 2)
            with patch.object(gateway, 'execute', AsyncMock(return_value='ok')) as execute:
                await gateway.route('cx/test-model', 'hello')
                execute.assert_awaited_once_with('codex', 'test-model', 'hello')

    async def test_real_subprocess_stdin_and_codex_output(self):
        # Exercise real process I/O with a local fake CLI; no provider requests.
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / 'fake.py'
            script.write_text('import sys, json\nfrom pathlib import Path\n'
                              'prompt = sys.stdin.read()\n'
                              'if sys.argv[1] == "codex": Path("answer.txt").write_text(prompt)\n'
                              'else: print(json.dumps({"result": prompt, "is_error": False}))\n')
            for provider in ('claude', 'codex'):
                with patch.object(gateway, 'command', return_value=[sys.executable, str(script), provider]):
                    prompt = 'literal $(touch bad) ; `echo bad` unicode: नमस्ते'
                    self.assertEqual(await gateway.execute(provider, None, prompt), prompt)

    async def test_timeout_and_exit_error(self):
        with patch.object(gateway, 'TIMEOUT', .1), patch.object(gateway, 'command', return_value=[
            sys.executable, '-c', 'import time; time.sleep(30)']):
            with self.assertRaises(gateway.APIError) as error:
                await gateway.execute('claude', None, 'hello')
            self.assertEqual(error.exception.status, 504)
        with patch.object(gateway, 'command', return_value=[sys.executable, '-c', 'raise SystemExit(7)']):
            with self.assertRaises(gateway.APIError) as error:
                await gateway.execute('claude', None, 'hello')
            self.assertEqual(error.exception.status, 502)


if __name__ == '__main__':
    unittest.main()
