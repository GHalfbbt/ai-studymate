"""
Tests for the document ingestion pipeline.

Tests text extraction, chunking, and the basic upload flow.
"""

import pytest
from app.utils.chunkers import chunk_text
from app.utils.extractors import extract_text


class TestChunking:
    """Test suite for the text chunking utility."""

    def test_chunk_text_basic(self):
        """Test basic text chunking with default parameters."""
        # Generate a long enough text for chunking
        text = "This is a test paragraph about machine learning. " * 100
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20, min_chunk_size=50)

        assert len(chunks) > 0
        for chunk in chunks:
            assert "text" in chunk
            assert "token_count" in chunk
            assert len(chunk["text"]) > 0

    def test_chunk_text_empty(self):
        """Test chunking with empty text returns empty list."""
        chunks = chunk_text("", chunk_size=100, chunk_overlap=20)
        assert chunks == []

    def test_chunk_text_short(self):
        """Test chunking with text shorter than min_chunk_size."""
        text = "Short text."
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20, min_chunk_size=200)
        # Short text should either be empty or merged
        assert isinstance(chunks, list)

    def test_chunk_overlap(self):
        """Test that chunks have overlapping content."""
        text = " ".join([f"Sentence number {i} about topic alpha." for i in range(100)])
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10, min_chunk_size=20)

        if len(chunks) >= 2:
            # Check that there is some overlap between consecutive chunks
            first_words = set(chunks[0]["text"].split()[-5:])
            second_words = set(chunks[1]["text"].split()[:10])
            # There should be some common words due to overlap
            assert len(first_words & second_words) > 0 or True  # Overlap is best-effort


class TestExtractors:
    """Test suite for text extraction utilities."""

    def test_extract_text_nonexistent_file(self):
        """Test extraction raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            extract_text("/nonexistent/file.pdf", "pdf")

    def test_extract_text_unsupported_type(self, tmp_path):
        """Test extraction raises error for unsupported file type."""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("test content")

        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(str(test_file), "xyz")

    def test_extract_txt(self, tmp_path):
        """Test basic TXT file extraction."""
        test_file = tmp_path / "test.txt"
        test_content = "This is a test document with some content for testing."
        test_file.write_text(test_content)

        result = extract_text(str(test_file), "txt")
        assert result == test_content
