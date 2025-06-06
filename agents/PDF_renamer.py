"""
Title: Modular PDF Renamer (LLM-agnostic) [Relocated to agents/]
Description: Renames PDFs in a directory using user-selected LLM (Anthropic, OpenAI, etc.) and prompt file. Extensible for CLI or web UI. Updates filenames and PDF metadata.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-06-06 (moved to agents package)
Dependencies: PyPDF2, anthropic, openai, python-dotenv, pathlib, typing
Abstract Spec: Provider abstraction and prompt decoupling enable flexible, testable, and future-proof document workflows.
"""

import os
import re
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader, PdfWriter

from adapters.llm_provider import get_llm_provider
from core.log_utils import log_event

# --- Prompt Loader ---

def load_prompt(prompt_path: Path) -> str:
    """Load prompt text from a file path."""
    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()

# --- PDF Extraction ---

def extract_first_n_pages_text(pdf_path: Path, n: int = 5, verbose: bool = False) -> Optional[str]:
    """Extract and return text from the first *n* pages of a PDF."""
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            log_event(f"[WARN] No pages found in {pdf_path.name}", verbose)
            return None
        pages = min(len(reader.pages), n)
        texts = [reader.pages[i].extract_text().strip() for i in range(pages) if reader.pages[i].extract_text()]
        return "\n\n".join(texts) if texts else None
    except Exception as exc:  # noqa: disable=broad-except
        log_event(f"[ERROR] Failed to extract from {pdf_path.name}: {exc}", verbose)
        return None

# --- Filename Sanitisation ---

def sanitize_filename(raw: str, limit: int = 200) -> str:
    """Sanitise a string to be used safely as a filename."""
    cleaned = re.sub(r"[^\w\s\-\(\)&]", "", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]

# --- Destination Path Helper ---

def make_destination_path(base_dir: Path, proposed: str) -> Path:
    """Return a unique destination Path for the proposed filename within *base_dir*."""
    if not proposed.lower().endswith(".pdf"):
        proposed += ".pdf"
    candidate = base_dir / proposed
    counter = 1
    while candidate.exists():
        stem, ext = os.path.splitext(proposed)
        candidate = base_dir / f"{stem}_{counter}{ext}"
        counter += 1
    return candidate

# --- PDF Metadata Update ---

def update_and_save_pdf_metadata(src_pdf: Path, dest_pdf: Path, author: str, title: str, date_str: str, verbose: bool = False) -> bool:
    """Copy *src_pdf* to *dest_pdf* updating PDF metadata along the way."""
    try:
        reader = PdfReader(str(src_pdf))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        metadata = {
            "/Author": author,
            "/Title": title,
            "/CreationDate": f"D:{date_str}0101000000Z",
        }
        writer.add_metadata(metadata)
        temp_path = dest_pdf.with_suffix(dest_pdf.suffix + ".tmp")
        with open(temp_path, "wb") as out_file:
            writer.write(out_file)
        temp_path.replace(dest_pdf)
        log_event(f"[INFO] Updated metadata for {src_pdf.name} -> {dest_pdf.name}", verbose)
        return True
    except Exception as exc:  # noqa: disable=broad-except
        log_event(f"[ERROR] Failed to update metadata for {src_pdf.name}: {exc}", verbose)
        return False

# --- Single PDF Processing ---

def process_single_pdf(pdf_path: Path, llm, prompt: str, n_pages: int = 5, verbose: bool = False):
    """Process a single PDF – rename and embed metadata."""
    log_event(f"[INFO] Processing {pdf_path.name}", verbose)
    extracted = extract_first_n_pages_text(pdf_path, n_pages, verbose)
    if not extracted:
        log_event(f"[WARN] Skipping {pdf_path.name}: no text extracted", verbose)
        return pdf_path

    guessed = llm.extract_metadata(prompt, extracted)
    if not guessed:
        log_event(f"[WARN] Skipping {pdf_path.name}: metadata guess failed", verbose)
        return pdf_path

    candidate = f"{guessed['author']} - {guessed['title']} ({guessed['pubdate']})"
    clean_candidate = sanitize_filename(candidate)
    dest_path = make_destination_path(pdf_path.parent, clean_candidate)

    if update_and_save_pdf_metadata(
        pdf_path,
        dest_path,
        sanitize_filename(guessed["author"]),
        sanitize_filename(guessed["title"]),
        guessed["pubdate"],
        verbose,
    ):
        pdf_path.unlink(missing_ok=True)
        log_event(f"[INFO] Renamed '{pdf_path.name}' -> '{dest_path.name}'", verbose)
        return dest_path

    log_event(f"[ERROR] Failed to process '{pdf_path.name}'", verbose)
    return pdf_path

# --- Directory Batch Processing ---

def process_pdf_directory(directory: Path, llm=None, prompt: str | None = None, n_pages: int = 5, verbose: bool = False):
    """Batch-process all PDFs in *directory*."""
    log_event(f"[INFO] Starting PDF batch in {directory}", verbose)
    if llm is None:
        llm = get_llm_provider(workflow="identify")
    if prompt is None:
        prompt = load_prompt(Path(__file__).parent / "PDF_renamer_prompt.txt")

    pdfs = sorted(
        (p for p in directory.iterdir() if p.suffix.lower() == ".pdf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for pdf in pdfs:
        process_single_pdf(pdf, llm, prompt, n_pages, verbose)
    log_event("[DONE] PDF processing completed.", verbose)
