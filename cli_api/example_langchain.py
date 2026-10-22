"""Run from the project root: .venv/bin/python -m cli_api.example_langchain."""
import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
llm = ChatOpenAI(
    base_url=os.getenv('CLI_API_BASE_URL', 'http://localhost:8088/v1'),
    api_key=os.getenv('CLI_API_KEY') or 'local-learning',
    model=os.getenv('CLI_API_MODEL', 'auto'),
    timeout=600,
    max_retries=0,
    use_responses_api=False,
)

if __name__ == '__main__':
    print(llm.invoke([
        ('system', 'You are a concise Python tutor.'),
        ('human', 'Explain a Python generator with a short example.'),
    ]).content)
