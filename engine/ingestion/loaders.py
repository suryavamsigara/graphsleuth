from pathlib import Path

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