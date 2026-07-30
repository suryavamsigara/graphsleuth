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
    """CPU bound model2vec (local dev)"""
    def __init__(self, model_name: str, dimensionality: int = 128):
        from model2vec import StaticModel
        self.model = StaticModel.from_pretrained(model_name, dimensionality=dimensionality)

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]


class HFSpacesEncoder(EmbeddingEncoder):
    """HTTP call to HF Spaces embedding service."""
    def __init__(self, space_url: str | None = None, api_key: str | None = None):
        self.space_url = (space_url or os.getenv("HF_SPACE_URL", "")).rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(timeout=60.0)

    def encode(self, texts: str | list[str]) -> list[list[float]]:
        if isinstance(texts, str):
            texts = [texts]
        payload = {"texts": texts}
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = self._client.post(
            f"{self.space_url}/embed",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]