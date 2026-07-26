import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_openai():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY not set.")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def get_ollama():
    ollama_host = os.getenv("OLLAMA_HOST", "localhost:11434")
    if not ollama_host.startswith("http"):
        ollama_host = f"http://{ollama_host}"
    if not ollama_host.endswith("/v1"):
        ollama_host = f"{ollama_host}/v1"

    return OpenAI(
        base_url=ollama_host,
        api_key="ollama"
    )
