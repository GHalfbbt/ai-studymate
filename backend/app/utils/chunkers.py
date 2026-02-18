"""
Text chunking utilities for document processing.

Implements recursive text splitting with configurable chunk sizes
and overlap. Designed to keep semantic coherence by splitting
at paragraph/sentence boundaries when possible.
"""

import re
from typing import List, Dict


def chunk_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
    min_chunk_size: int = 200,
) -> List[Dict]:
    """
    Split text into overlapping chunks for embedding.

    Uses a hierarchical splitting strategy:
    1. First tries to split at paragraph boundaries (double newline)
    2. Then at sentence boundaries (period + space)
    3. Falls back to word boundaries
    4. Last resort: character-level split

    Each chunk includes overlap with the previous chunk to maintain
    context continuity for the embedding model.

    Args:
        text: Full text to split into chunks
        chunk_size: Target number of tokens per chunk (approximate,
                   calculated as words since tokenizer varies by model)
        chunk_overlap: Number of tokens to overlap between chunks
        min_chunk_size: Minimum tokens for a valid chunk (smaller chunks
                       are merged with adjacent ones or discarded)

    Returns:
        List of dicts, each containing:
            - text: The chunk text content
            - token_count: Approximate token count (word-based estimate)
            - start_char: Starting character index in original text
            - end_char: Ending character index in original text
    """
    if not text or not text.strip():
        return []

    # Clean whitespace while preserving paragraph structure
    text = _normalize_whitespace(text)

    # Split into semantic segments (paragraphs first)
    segments = _split_into_segments(text)

    # Build chunks from segments with overlap
    chunks = _build_chunks(segments, chunk_size, chunk_overlap, min_chunk_size)

    return chunks


def _normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace while preserving paragraph breaks.

    Replaces multiple consecutive newlines with double newlines,
    and multiple spaces with single spaces.

    Args:
        text: Raw text with potentially messy whitespace

    Returns:
        str: Cleaned text with normalized spacing
    """
    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Replace multiple spaces with single space
    text = re.sub(r" {2,}", " ", text)
    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _split_into_segments(text: str) -> List[str]:
    """
    Split text into semantic segments at natural boundaries.

    Priority order:
    1. Paragraphs (double newline)
    2. Sentences (period followed by space/newline)

    Args:
        text: Normalized text

    Returns:
        List of text segments
    """
    # First split by paragraphs
    paragraphs = text.split("\n\n")

    segments = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue

        # If paragraph is short enough, keep it as a single segment
        word_count = len(paragraph.split())
        if word_count <= 800:  # Max words before further splitting
            segments.append(paragraph.strip())
        else:
            # Split long paragraphs into sentences
            sentences = _split_sentences(paragraph)
            segments.extend(sentences)

    return segments


def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex.

    Handles common sentence endings: . ! ?
    Preserves abbreviations and decimal numbers.

    Args:
        text: Text to split into sentences

    Returns:
        List of sentences
    """
    # Split on sentence endings followed by space and uppercase letter
    # This avoids splitting on abbreviations like "Dr." or "U.S.A."
    sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])"
    sentences = re.split(sentence_pattern, text)

    # Filter empty sentences and strip whitespace
    return [s.strip() for s in sentences if s.strip()]


def _build_chunks(
    segments: List[str],
    chunk_size: int,
    chunk_overlap: int,
    min_chunk_size: int,
) -> List[Dict]:
    """
    Build overlapping chunks from text segments.

    Accumulates segments until the chunk_size target is reached,
    then creates a chunk with overlap from the previous one.

    Args:
        segments: List of text segments to combine into chunks
        chunk_size: Target token count per chunk
        chunk_overlap: Token overlap between consecutive chunks
        min_chunk_size: Minimum valid chunk size

    Returns:
        List of chunk dictionaries with text and metadata
    """
    chunks = []
    current_segments = []
    current_token_count = 0
    char_offset = 0

    for segment in segments:
        segment_tokens = _estimate_tokens(segment)

        # If adding this segment would exceed the target, create a chunk
        if current_token_count + segment_tokens > chunk_size and current_segments:
            chunk_text = "\n\n".join(current_segments)
            chunks.append({
                "text": chunk_text,
                "token_count": _estimate_tokens(chunk_text),
                "start_char": char_offset,
                "end_char": char_offset + len(chunk_text),
            })

            # Keep overlap by retaining the last segment(s)
            overlap_tokens = 0
            overlap_segments = []
            for seg in reversed(current_segments):
                seg_tokens = _estimate_tokens(seg)
                if overlap_tokens + seg_tokens <= chunk_overlap:
                    overlap_segments.insert(0, seg)
                    overlap_tokens += seg_tokens
                else:
                    break

            # Update offset for overlap
            overlap_text = "\n\n".join(overlap_segments)
            char_offset += len(chunk_text) - len(overlap_text)

            current_segments = overlap_segments
            current_token_count = overlap_tokens

        current_segments.append(segment)
        current_token_count += segment_tokens

    # Handle the last chunk
    if current_segments:
        chunk_text = "\n\n".join(current_segments)
        token_count = _estimate_tokens(chunk_text)

        # Only add if it meets minimum size requirement
        if token_count >= min_chunk_size:
            chunks.append({
                "text": chunk_text,
                "token_count": token_count,
                "start_char": char_offset,
                "end_char": char_offset + len(chunk_text),
            })
        elif chunks:
            # Merge small last chunk with the previous one
            prev = chunks[-1]
            prev["text"] += "\n\n" + chunk_text
            prev["token_count"] = _estimate_tokens(prev["text"])
            prev["end_char"] = char_offset + len(chunk_text)

    return chunks


def _estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.

    Uses a simple word-based heuristic: approximately 1.3 tokens per word
    for English text. This is a reasonable approximation for most
    transformer tokenizers.

    Args:
        text: Text to estimate token count for

    Returns:
        int: Estimated number of tokens
    """
    word_count = len(text.split())
    return int(word_count * 1.3)
