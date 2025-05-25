"""
Title: Modular PDF Renamer (LLM-agnostic)
Description: Renames PDFs in a directory using user-selected LLM (Anthropic, OpenAI, etc.) and prompt file. Extensible for CLI or web UI. Updates filenames and PDF metadata.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-05-11
Dependencies: PyPDF2, anthropic, openai, python-dotenv, pathlib, typing
Design Rationale: Provider abstraction and prompt decoupling enable flexible, testable, and future-proof document workflows.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
import argparse

from adapters.llm_provider import get_llm_provider
from core.log_utils import log_event

# --- Prompt Loader ---
def load_prompt(prompt_path: Path) -> str:
    """
    Purpose: Load the LLM prompt from a file.
    Inputs: prompt_path (Path)
    Outputs: prompt string
    Role: Decouples prompt editing from code.
    """
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

# --- PDF Extraction ---
def extract_first_n_pages_text(pdf_path: Path, n: int = 5, verbose: bool = False) -> Optional[str]:
    """
    Purpose: Extract text from the first n pages of a PDF file.
    Inputs: pdf_path (Path), n (int), verbose (bool)
    Outputs: Extracted text or None
    Role: Supplies raw text for LLM analysis.
    """
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            log_event(f"[WARN] No pages found in {pdf_path.name}", verbose)
            return None
        num_pages = min(len(reader.pages), n)
        texts = []
        for i in range(num_pages):
            page_text = reader.pages[i].extract_text()
            if page_text:
                texts.append(page_text.strip())
        return "\n\n".join(texts) if texts else None
    except Exception as e:
        log_event(f"[ERROR] Failed to extract from {pdf_path.name}: {e}", verbose)
        return None

# --- Filename Sanitization ---
def sanitize_filename(raw: str, limit: int = 200) -> str:
    """
    Purpose: Remove forbidden/special chars, normalize whitespace, and ensure candidate filename is safe & not too long.
    Inputs: raw (str), limit (int)
    Outputs: cleaned, truncated string
    Role: Prevents OS errors, improves human readability in filenames.
    """
    cleaned = re.sub(r"[^\w\s\(\)\-\&]", "", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]

# --- Destination Path Generation ---
def make_destination_path(base_dir: Path, proposed: str) -> Path:
    """
    Purpose: Given a directory and candidate filename, return a unique, absolute Path that doesn't overwrite existing files.
    Inputs: base_dir (Path), proposed (str)
    Outputs: Path object
    Role: File system collision avoidance, multi-run safety.
    """
    base_name = proposed
    if not base_name.lower().endswith(".pdf"):
        base_name += ".pdf"
    candidate = base_dir / base_name
    counter = 1
    while candidate.exists():
        stem, ext = os.path.splitext(base_name)
        candidate = base_dir / f"{stem}_{counter}{ext}"
        counter += 1
    return candidate

# --- PDF Metadata Update ---
def update_and_save_pdf_metadata(src_pdf: Path, dest_pdf: Path, author: str, title: str, date_str: str, verbose: bool = False) -> bool:
    """
    Purpose: Copy PDF, update XMP/document metadata, save as dest_pdf.
    Inputs: src_pdf (Path), dest_pdf (Path), author/title/date_str (str), verbose (bool)
    Outputs: True if successful, False on failure
    Role: Ensures both correct filename and internal PDF metadata for archival integrity.
    """
    try:
        reader = PdfReader(str(src_pdf))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        year_candidate = str(date_str)
        metadata = {
            "/Author": author,
            "/Title": title,
            "/CreationDate": f"D:{year_candidate}0101000000Z"
        }
        writer.add_metadata(metadata)
        temp_path = dest_pdf.parent / (dest_pdf.name + ".tmp")
        with open(temp_path, "wb") as out_f:
            writer.write(out_f)
        temp_path.replace(dest_pdf)
        log_event(f"[INFO] Updated metadata for {src_pdf.name} -> {dest_pdf.name}", verbose)
        return True
    except Exception as e:
        log_event(f"[ERROR] Failed to update metadata for {src_pdf.name}: {e}", verbose)
        return False

# --- Single PDF Processing ---
def process_single_pdf(pdf_path: Path, llm, prompt: str, n_pages: int = 5, verbose: bool = False):
    """
    Purpose: For a single PDF, extract, AI-infer metadata, attempt rename and metadata write.
    Inputs: pdf_path (Path), llm (LLMProvider), prompt (str), n_pages (int), verbose (bool)
    Outputs: Path to new PDF file on success (or original path if unchanged/fail)
    Role: Unit of work for workflow; enables granular testing and extension.
    """
    log_event(f"[INFO] Processing {pdf_path.name}", verbose)
    extracted = extract_first_n_pages_text(pdf_path, n=n_pages, verbose=verbose)
    if not extracted:
        log_event(f"[WARN] Skipping {pdf_path.name}: no text found.", verbose)
        return pdf_path
    guessed = llm.extract_metadata(prompt, extracted)
    if not guessed:
        log_event(f"[WARN] Skipping {pdf_path.name}: LLM metadata guess failed or unreliable.", verbose)
        return pdf_path
    candidate_name = f"{guessed['author']} - {guessed['title']} ({guessed['pubdate']})"
    clean_file = sanitize_filename(candidate_name)
    new_path = make_destination_path(pdf_path.parent, clean_file)
    if update_and_save_pdf_metadata(pdf_path, new_path, sanitize_filename(guessed['author']), sanitize_filename(guessed['title']), guessed['pubdate'], verbose=verbose):
        pdf_path.unlink(missing_ok=True)
        log_event(f"[INFO] Renamed '{pdf_path.name}' → '{new_path.name}'", verbose)
        return new_path
    else:
        log_event(f"[ERROR] Failed to process '{pdf_path.name}': metadata/write error.", verbose)
        return pdf_path

# --- Directory Batch Processing ---
def process_pdf_directory(directory: Path, llm, prompt: str, n_pages: int = 5, verbose: bool = False):
    """
    Purpose: For all PDFs in directory, apply process_single_pdf() in sorted, recent-first order.
    Inputs: directory (Path), llm (LLMProvider), prompt (str), n_pages (int), verbose (bool)
    Outputs: None (logs progress)
    Role: Batch driver for workflow; entrypoint for CLI, scripting, or extension.
    """
    log_event(f"[INFO] Starting batch PDF processing in {directory}", verbose)
    pdfs = sorted((f for f in directory.iterdir() if f.suffix.lower() == ".pdf" and f.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    for pdf_path in pdfs:
        process_single_pdf(pdf_path, llm, prompt, n_pages=n_pages, verbose=verbose)
    log_event("[DONE] Finished processing all PDFs!", verbose)
