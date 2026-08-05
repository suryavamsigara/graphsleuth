"""
Local + HF Spaces encoder
"""

import os
import httpx
import numpy as np

class EmbeddingEncoder:
    """Base interface. Returns list[float] per text."""
    def encode(self, texts: str | list[str]) -> list[list[float]]:
        raise NotImplementedError

    def encode_single(self, text: str) -> list[float]:
        return self.encode(text)[0]

class LocalEncoder(EmbeddingEncoder):
    """CPU bound sentence transformers (local dev)"""
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimensionality: int = 384):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name)
        self.dimensionality = dimensionality

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings.tolist()


class RemoteEncoder(EmbeddingEncoder):
    """HTTP call to HF Spaces embedding service."""
    def __init__(self, space_url: str | None = None, api_key: str | None = None):
        self.space_url = (space_url or os.getenv("HF_SPACE_URL", "")).rstrip("/")
        self.api_key = api_key
        if not self.space_url:
            raise ValueError("HF_SPACE_URL env var required for HFSpacesEncoder")
        self._client = httpx.Client(timeout=60.0)

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = self._client.post(
            f"{self.space_url}/embed",
            json={"texts": texts},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def health(self) -> dict:
        try:
            r = self._client.get(f"{self.space_url}/health", timeout=10.0)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"status": "error", "detail": str(e)}