from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?:(?<=[.!?])[ \t]+|(?<=\.)\r?\n+)", text)
            if sentence.strip()
        ]
        size = self.max_sentences_per_chunk
        return [" ".join(sentences[start : start + size]) for start in range(0, len(sentences), size)]


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]
        if not remaining_separators or remaining_separators[0] == "":
            return [
                current_text[start : start + self.chunk_size]
                for start in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        if separator not in current_text:
            return self._split(current_text, remaining_separators[1:])

        parts = current_text.split(separator)
        chunks: list[str] = []
        current_chunk = ""
        last_index = len(parts) - 1

        for index, part in enumerate(parts):
            piece = part + separator if index < last_index else part
            if not piece:
                continue

            subchunks = (
                [piece]
                if len(piece) <= self.chunk_size
                else self._split(piece, remaining_separators[1:])
            )
            for subchunk in subchunks:
                if current_chunk and len(current_chunk) + len(subchunk) > self.chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = subchunk
                else:
                    current_chunk += subchunk

        if current_chunk:
            chunks.append(current_chunk)
        return chunks


class HeadingChunker:
    """Split structured text at Markdown and common legal-section headings."""

    HEADING_PATTERN = re.compile(
        r"(?m)^(?:"
        r"#{1,6}\s+.+"
        r"|(?:\u0110i\u1ec1u|\u0110I\u1ec0U)\s+\d+[^\n]*"
        r"|(?:Ch\u01b0\u01a1ng|CH\u01af\u01a0NG)\s+[IVXLCDM\d]+[^\n]*"
        r"|[IVXLCDM]+\.\s*[^\W\d_][^\n]*"
        r")$"
    )

    def __init__(self, chunk_size: int = 800) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            return self._fallback.chunk(text)

        chunks: list[str] = []
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chunks.extend(self._fallback.chunk(preamble))

        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = text[match.start() : end].strip()
            heading = match.group(0).strip()
            chunks.extend(self._split_section(section, heading))
        return chunks

    def _split_section(self, section: str, heading: str) -> list[str]:
        if len(section) <= self.chunk_size:
            return [section]

        prefix = f"{heading}\n"
        available_size = self.chunk_size - len(prefix)
        if available_size <= 0:
            return self._fallback.chunk(section)

        body = section[len(heading) :].lstrip()
        if not body:
            return [heading]

        body_chunks = RecursiveChunker(chunk_size=available_size).chunk(body)
        return [prefix + body_chunk for body_chunk in body_chunks]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_product = math.sqrt(_dot(vec_a, vec_a) * _dot(vec_b, vec_b))
    if magnitude_product == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / magnitude_product


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        overlap = min(50, max(0, chunk_size - 1))
        strategy_chunks = {
            "fixed_size": FixedSizeChunker(chunk_size, overlap).chunk(text),
            "by_sentences": SentenceChunker().chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        return {
            name: {
                "count": len(chunks),
                "avg_length": sum(map(len, chunks)) / len(chunks) if chunks else 0.0,
                "chunks": chunks,
            }
            for name, chunks in strategy_chunks.items()
        }
