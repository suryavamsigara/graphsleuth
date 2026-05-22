import os
from openai import OpenAI

def get_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPSEEK_API_KEY not set.")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )