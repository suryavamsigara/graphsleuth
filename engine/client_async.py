import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

def get_async_openai_client() -> AsyncOpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY not set.")
    
    return AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def get_async_ollama_client() -> AsyncOpenAI:
    ollama_host = os.getenv("OLLAMA_HOST", "localhost:11434")
    if not ollama_host.startswith("http"):
        ollama_host = f"http://{ollama_host}"
    if not ollama_host.endswith("/v1"):
        ollama_host = f"{ollama_host}/v1"

    return AsyncOpenAI(
        base_url=ollama_host,
        api_key="ollama"
    )
