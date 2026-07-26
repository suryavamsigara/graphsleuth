import os
import uuid
from pathlib import Path

from graph import KnowledgeGraph, Node, Edge, Chunk, Document
from extractor import EntityExtractor


def extract_text_from_file(file_path: str) -> str:
    """
    Extracts raw text from a file.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    text_extensions = {".txt", ".md", ".py"}
    if suffix in text_extensions or suffix == "":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to read {file_path}: {e}")

    if suffix == ".pdf":
        try:
            import pypdf
            text = ""
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            raise ImportError("pypdf required for PDF support. Install: uv add pypdf")
        except Exception as e:
            raise ValueError(f"Failed to extract PDF {file_path}: {e}")

    raise ValueError(f"Unsupported file type: {suffix}. Supported: {text_extensions}")


def chunk_by_paragraphs(text: str, max_chars: int = 1500, overlap: int = 200) -> list[str]:
    """
    Splits text into paragraphs.
    """
    # Split on double newlines
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in raw_paragraphs:
        # If a single paragraph exceeds max_chars, split by sentences
        if len(para) > max_chars:
            sentences = split_into_sentences(para)
            for sent in sentences:
                if len(current_chunk) + len(sent) + 1 <= max_chars:
                    current_chunk += " " + sent if current_chunk else sent
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sent
            continue

        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add overlap: each chunk starts with last overlap chars of previous
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i-1][-overlap:] if len(chunks[i-1]) > overlap else chunks[i-1]
            overlapped.append(prev_tail + "\n\n" + chunks[i])
        chunks = overlapped
    return chunks


def split_into_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]




if __name__=="__main__":
    test_text = """
    In 2015, Sam Altman and Elon Musk founded OpenAI as a non-profit.
    In 2019, Sam Altman became CEO of OpenAI.
    In 2022, OpenAI released ChatGPT, which became the fastest-growing consumer app.
    Microsoft invested $10 billion into OpenAI in January 2023.
    Elon Musk left the OpenAI board in 2018 and later founded xAI in 2023.
    """
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_text)
        temp_path = f.name

    ext = extract_text_from_file(temp_path)
    print(ext)
    chunks = chunk_by_paragraphs(ext)
    print("="*50)
    print(chunks)
