"""
Takes raw text and returns list of chunks
"""

from typing import Optional

from models import Chunk


class Chunker:
    def __init__(self, chunk_size: int = 300, overlap: int = 50, strategy: Optional[str] = None):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = strategy

    def chunk_content(self, content: str, source_doc: str) -> list[Chunk]:
        """
        Returns list of Chunk objects.
        """
        words: list[str] = content.split(' ')
        
        chunks: list[Chunk] = []
        chunk_index = 0

        if self.chunk_size <= self.overlap:
            raise ValueError(f"Overlap ({self.overlap}) must be less that ({self.chunk_size})")

        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_text = ' '.join(words[i:i+self.chunk_size]).strip(',')
            chunk = Chunk(
                text=chunk_text,
                source_doc=source_doc,
                index=chunk_index

            )
            chunks.append(chunk)
            chunk_index += 1
        
        return chunks
