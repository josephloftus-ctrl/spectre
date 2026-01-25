"""PDF text extraction using pdfplumber."""

import pdfplumber
from pathlib import Path


def extract_text_from_pdf(pdf_path: Path | str) -> str:
    """Extract text from PDF maintaining layout."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if text:
                text_parts.append(text)

    return "\n".join(text_parts)


def extract_tables_from_pdf(pdf_path: Path | str) -> list[list[list[str]]]:
    """Extract tables from PDF as list of tables, each table is list of rows."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            all_tables.extend(tables or [])

    return all_tables
