from typing import List

def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """
    Split text into overlapping chunks.
    chunk_size: max words per chunk
    overlap: words shared between consecutive chunks
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk.strip())
        start += chunk_size - overlap  # slide with overlap

    return [c for c in chunks if len(c.strip()) > 50]  # skip tiny chunks


def chunk_code(code: str, max_lines: int = 50) -> List[str]:
    """
    Split code by lines, keeping logical blocks together.
    """
    lines = code.split("\n")
    chunks = []
    current = []

    for line in lines:
        current.append(line)
        if len(current) >= max_lines:
            chunks.append("\n".join(current))
            current = current[-10:]  # keep last 10 lines as overlap

    if current:
        chunks.append("\n".join(current))

    return [c for c in chunks if c.strip()]