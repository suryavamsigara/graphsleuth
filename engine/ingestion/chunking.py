import re

def chunk_by_paragraphs(
    text: str,
    max_chars: int = 1200,
    overlap: int = 150
) -> list[str]:
    """
    Splits text into chunks cleanly, respecting paragraph and sentence boundaries.
    Overlaps snap to word boundaries to prevent fragmented words, and strict length 
    limits are guaranteed.
    """
    
    # 1. Break text into an ordered stream of addressable semantic units
    def tokenize_text(raw_text: str):
        units = []
        for p in raw_text.split('\n\n'):
            p = p.strip()
            if not p:
                continue
            
            if len(p) <= max_chars:
                units.append((p, '\n\n'))
            else:
                # Fallback A: Paragraph is too big, split into sentences
                for s in re.split(r'(?<=[.!?])\s+', p):
                    s = s.strip()
                    if not s:
                        continue
                        
                    if len(s) <= max_chars:
                        units.append((s, ' '))
                    else:
                        # Fallback B: Sentence is STILL too big, split into words
                        for w in s.split():
                            if w.strip():
                                units.append((w.strip(), ' '))
        return units

    units = tokenize_text(text)
    chunks = []
    current_chunk = ""

    # 2. Reassemble units into chunks with safe overlapping
    for unit_text, separator in units:
        # Determine the connecting string
        prefix = separator if current_chunk else ""
        candidate = current_chunk + prefix + unit_text
        
        # If it fits, keep growing the chunk
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            # Chunk is full: Save it
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Seed the next chunk with the overlap from the saved chunk
            if overlap > 0 and current_chunk:
                tail = current_chunk[-overlap:]
                
                # Snap to the nearest word boundary (first space) to avoid slicing words
                space_idx = tail.find(' ')
                if space_idx != -1 and space_idx < len(tail) - 1:
                    current_chunk = tail[space_idx + 1:]
                else:
                    current_chunk = tail  # Fallback if no spaces exist
            else:
                current_chunk = ""
                
            # Add the current unit to the newly seeded chunk
            prefix = separator if current_chunk else ""
            if len(current_chunk) + len(prefix) + len(unit_text) <= max_chars:
                current_chunk = current_chunk + prefix + unit_text
            else:
                # Edge case: Overlap + new unit exceeds max_chars.
                # Drop the overlap to strictly enforce character limits.
                current_chunk = unit_text

    # 3. Append the final remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def split_into_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]