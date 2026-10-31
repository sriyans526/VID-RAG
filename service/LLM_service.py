"""LLM provider configuration for VidRAG Advanced.

Cloud mode uses Ollama's OpenAI-compatible API; it does not require
an Ollama server or downloaded model on the user's computer.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load the project-root .env regardless of the terminal's working directory.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')


class LLMService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_llm():
        provider = os.getenv('LLM_PROVIDER', 'ollama_cloud').strip().lower()
        temperature = 0.1
        max_tokens = int(os.getenv('OLLAMA_NUM_PREDICT', '1024'))

        if provider == 'ollama_cloud':
            from langchain_openai import ChatOpenAI

            api_key = os.getenv('OLLAMA_API_KEY', '').strip()
            if not api_key:
                raise RuntimeError('OLLAMA_API_KEY is missing from the environment.')

            base_url = os.getenv(
                'OLLAMA_CLOUD_BASE_URL', 'https://ollama.com/v1'
            ).strip().rstrip('/')
            if not base_url.endswith('/v1'):
                base_url += '/v1'

            model = os.getenv(
                'OLLAMA_CLOUD_MODEL', 'nemotron-3-nano:30b-cloud'
            ).strip()
            if not model:
                raise RuntimeError('OLLAMA_CLOUD_MODEL is empty.')

            return ChatOpenAI(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,
                max_retries=2,
            )

        if provider == 'ollama':
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=os.getenv('OLLAMA_MODEL', 'nemotron-3-nano:30b'),
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                temperature=temperature,
                reasoning=False,
                num_predict=max_tokens,
            )

        if provider == 'gemini':
            from langchain_google_genai import ChatGoogleGenerativeAI

            if not os.getenv('GOOGLE_API_KEY'):
                raise RuntimeError('GOOGLE_API_KEY is missing from the environment.')
            return ChatGoogleGenerativeAI(
                model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
                temperature=temperature,
            )

        raise ValueError(
            f'Unsupported LLM_PROVIDER={provider!r}. '
            'Choose ollama_cloud, ollama, or gemini.'
        )
