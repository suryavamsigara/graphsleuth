"""
Local + Remote encoder
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

class EmbeddingEncoder:
    """Base interface. Returns list[float] per text."""
    def encode(self, texts: str | list[str]) -> list[list[float]]:
        raise NotImplementedError

    def encode_single(self, text: str) -> list[float]:
        return self.encode(text)[0]

# class LocalEncoder(EmbeddingEncoder):
#     """CPU bound sentence transformers (local dev)"""
#     def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimensionality: int = 384):
#         from sentence_transformers import SentenceTransformer
#         self.model_name = model_name
#         self.model = SentenceTransformer(self.model_name)
#         self.dimensionality = dimensionality

#     def encode(self, texts: str | list[str]) -> list[list[float]]:
#         if isinstance(texts, str):
#             texts = [texts]
#         embeddings = self.model.encode(
#             texts,
#             convert_to_numpy=True,
#             show_progress_bar=False
#         )
#         return embeddings.tolist()


class RemoteEncoder(EmbeddingEncoder):
    """HTTP call to cloudflare embedding service."""
    def __init__(self, model_name: str, dimensionality: int = 384):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL_NAME")

        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID required for RemoteEncoder")
        if not self.api_token:
            raise ValueError("CLOUDFLARE_API_TOKEN required for RemoteEncoder")

        self.url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/{self.model_name}"
        
        self._client = httpx.Client(
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.api_token}"}
        )

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        is_single_str = isinstance(texts, str)
        
        payload = {"text": [texts] if is_single_str else texts}
            
        resp = self._client.post(self.url, json=payload)

        if resp.status_code != 200:
            print(f"[RemoteEncoder Error Body]: {resp.text}")
            resp.raise_for_status()

        resp.raise_for_status()
        data = resp.json()["result"]["data"]
        if len(texts) == 1 and isinstance(data[0], float):
            return [data]
        return data