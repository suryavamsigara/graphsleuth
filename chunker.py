"""
Takes raw text and returns list of chunks
"""

import uuid
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field

from client import get_client

@dataclass(frozen=True)
class Chunk:
    text: str
    source_doc: str
    index: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class Chunker:
    def __init__(self, chunk_size: int = 300, overlap: int = 50, strategy: Optional[str] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy

        self.chunks_list: dict[str, Chunk] = {}
    
    def create_chunk(self, chunk_text: str, source_doc: str, index: int) -> str:
        chunk = Chunk(
            text=chunk_text,
            source_doc=source_doc,
            index=index
        )

        self.chunks_list[chunk.id] = chunk
        return chunk.id

    def chunk_content(self, content: str) -> list[list[str]]:
        words: list[str] = content.split(' ')
        
        chunks: list[list[str]] = []

        if self.chunk_size <= self.overlap:
            raise ValueError(f"Overlap ({self.overlap}) must be less that ({self.chunk_size})")

        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunks.append(words[i:i+self.chunk_size])
        
        return chunks

    def get_chunks(self):
        return self.chunks_list
