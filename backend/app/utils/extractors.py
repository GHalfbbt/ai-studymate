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
    Extract text from a PDF file.

    Strategy:
    1. Try pdfplumber (best for text-based PDFs, handles complex layouts)
    2. Fallback to PyPDF2
    3. Fallback to OCR via Gemini Vision for scanned/image PDFs
    """
    # --- Attempt 1: pdfplumber ---
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        pass
    except Exception:
        pass

    # --- Attempt 2: PyPDF2 ---
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())
        if text_parts:
            return "\n\n".join(text_parts)
    except Exception:
        pass

    # --- Attempt 3: OCR via Gemini Vision ---
    try:
        return _ocr_pdf_with_gemini(file_path)
    except Exception as e:
        raise ValueError(
            f"Could not extract text from PDF. The file appears to be scanned/image-based "
            f"and OCR also failed: {str(e)}\n"
            f"Please ensure GEMINI_API_KEY is configured for scanned PDF support."
        )


def _ocr_pdf_with_gemini(file_path: str) -> str:
    """
    Use Gemini Vision to OCR a scanned PDF by converting pages to images.
    Each page is sent to Gemini as an image and the text is extracted.
    """
    import base64
    from app.core.config import settings

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured for OCR")

    # Convert PDF pages to images using PyPDF2 / PIL
    try:
        import fitz  # PyMuPDF
        pdf_doc = fitz.open(file_path)
    except ImportError:
        raise ValueError("PyMuPDF not installed. Cannot convert scanned PDF to images for OCR.")

    import httpx
    import json

    all_text = []
    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}/generateContent?key={settings.GEMINI_API_KEY}"
    )

    for page_num in range(min(len(pdf_doc), 50)):  # Max 50 pages
        page = pdf_doc[page_num]
        # Render page as image at 150 DPI
        mat = fitz.Matrix(150 / 72, 150 / 72)
        clip = page.get_pixmap(matrix=mat)
        img_bytes = clip.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode()

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extract ALL the text from this document page. Return ONLY the extracted text, no commentary."},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }]
        }

        response = httpx.post(gemini_url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            page_text = result["candidates"][0]["content"]["parts"][0]["text"]
            if page_text.strip():
                all_text.append(f"[Page {page_num + 1}]\n{page_text.strip()}")

    pdf_doc.close()

    if not all_text:
        raise ValueError("Gemini OCR returned no text from this PDF")
    
    print(f"  🔍 OCR completado con Gemini: {len(all_text)} páginas procesadas")
    return "\n\n".join(all_text)


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
