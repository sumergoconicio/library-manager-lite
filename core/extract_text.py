"""
core/extract_text.py | PDF Text Extraction Module
Purpose: Extract text from a single PDF file and save as .txt in the appropriate extract folder.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-23
Non-Std Deps: PyMuPDF (fitz)
Abstract Spec: Receives PDF path, extracts text, writes to .txt in extract folder, returns status.
"""

from pathlib import Path
import fitz  # PyMuPDF
from core.log_utils import log_event


def extract_text_from_pdf(pdf_path: Path, verbose: bool = False) -> str:
    """
    Purpose: Extract all text from a PDF file.
    Inputs: pdf_path (Path) - Path to the PDF file.
    Outputs: text (str) - The extracted text content.
    Role: Converts the PDF's content into plain text for saving.
    """
    log_event(f"[INFO] Extracting text from PDF: {pdf_path}", verbose)
    doc = fitz.open(str(pdf_path))
    text = "".join(page.get_text() for page in doc)
    log_event(f"[INFO] Extracted text length: {len(text)} chars from {pdf_path}", verbose)
    return text


def save_text_to_txt(text: str, output_path: Path, verbose: bool = False) -> None:
    """
    Purpose: Save extracted text to a text (.txt) file at the specified path.
    Inputs: text (str) - The text to save; output_path (Path) - Where to save the file.
    Outputs: None
    Role: Persists the extracted text for user access and further use.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(text)
    log_event(f"[INFO] Saved extracted text to: {output_path}", verbose)


def extract_and_save(pdf_path: Path, txt_path: Path, verbose: bool = False) -> bool:
    """
    Purpose: Extract text from PDF and save to txt file.
    Inputs: pdf_path (Path), txt_path (Path)
    Outputs: True if success, False otherwise.
    Role: Main subroutine for PDF text extraction.
    """
    try:
        log_event(f"[INFO] extract_and_save: {pdf_path} → {txt_path}", verbose)
        text = extract_text_from_pdf(pdf_path, verbose=verbose)
        save_text_to_txt(text, txt_path, verbose=verbose)
        return True
    except Exception as e:
        log_event(f"[ERROR] Failed to extract '{pdf_path}': {e}", verbose)
        return False
