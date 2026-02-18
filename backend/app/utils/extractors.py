"""
Text extraction utilities for different file formats.

Supports PDF, DOCX, TXT, and image files.
Each extractor returns plain text content from the file.
"""

import os
from typing import Optional


def extract_text(file_path: str, file_type: str) -> str:
    """
    Extract text content from a file based on its type.

    Dispatches to the appropriate extraction function based on file_type.

    Args:
        file_path: Absolute path to the file
        file_type: File type identifier (pdf, docx, txt, image)

    Returns:
        str: Extracted plain text content

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file type is not supported
        Exception: For extraction-specific errors
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    extractors = {
        "pdf": _extract_pdf,
        "docx": _extract_docx,
        "txt": _extract_txt,
        "image": _extract_image,
    }

    extractor = extractors.get(file_type)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type: '{file_type}'. "
            f"Supported types: {', '.join(extractors.keys())}"
        )

    return extractor(file_path)


def _extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyPDF2.

    Concatenates text from all pages with page separators.

    Args:
        file_path: Path to the PDF file

    Returns:
        str: Extracted text from all pages
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    text_parts = []

    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text.strip())

    if not text_parts:
        raise ValueError(
            "Could not extract text from PDF. "
            "The file may be scanned/image-based. "
            "Try uploading a text-based PDF."
        )

    return "\n\n".join(text_parts)


def _extract_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file using python-docx.

    Extracts text from all paragraphs and tables.

    Args:
        file_path: Path to the DOCX file

    Returns:
        str: Extracted text from paragraphs and tables
    """
    from docx import Document

    doc = Document(file_path)
    text_parts = []

    # Extract text from paragraphs
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text.strip())

    # Extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                text_parts.append(row_text)

    if not text_parts:
        raise ValueError("Could not extract text from DOCX. The file may be empty.")

    return "\n\n".join(text_parts)


def _extract_txt(file_path: str) -> str:
    """
    Read text from a plain text file.

    Tries UTF-8 encoding first, falls back to latin-1.

    Args:
        file_path: Path to the TXT file

    Returns:
        str: File content as text
    """
    # Try UTF-8 first (most common)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        pass

    # Fallback to latin-1 (handles most bytes)
    with open(file_path, "r", encoding="latin-1") as f:
        return f.read()


def _extract_image(file_path: str) -> str:
    """
    Extract text from an image file.

    Currently returns a placeholder message. Full OCR support
    can be added with pytesseract or a cloud vision API.

    Args:
        file_path: Path to the image file

    Returns:
        str: Description or OCR text from the image

    TODO: Implement OCR with pytesseract or cloud vision API
        This would require:
        - pip install pytesseract
        - Installing Tesseract OCR engine
        - Or using a cloud API like Google Vision
    """
    # For MVP, return a note that image OCR is not yet implemented
    # Images can still be stored and referenced
    return (
        f"[Image file: {os.path.basename(file_path)}] "
        "Image text extraction (OCR) is not yet implemented. "
        "This image has been stored for reference but its content "
        "cannot be searched or used for RAG queries yet."
    )
