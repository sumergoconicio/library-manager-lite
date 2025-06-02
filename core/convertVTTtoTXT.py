"""
core/convertVTTtoTXT.py | VTT to TXT Conversion Module
Purpose: Convert VTT subtitle files to plain text, extracting styled text and removing formatting tags
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-02
Non-Std Deps: None
Abstract Spec: Extracts styled lines from VTT files, strips tags, removes duplicates, saves as TXT, and deletes original VTT.
"""

from pathlib import Path
import re
import os
from core.log_utils import log_event

def extract_styled_lines(vtt_file_path: str) -> str:
    """
    Extract only lines containing styling tags from a VTT subtitle file, strip all tags,
    remove duplicates, and return plain text.
    
    Args:
        vtt_file_path (str): Path to the VTT file to convert
        
    Returns:
        str: Subtitle text in plain text format, only from styled lines with tags removed
    """
    path = Path(vtt_file_path)
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    txt_lines = []
    seen = set()
    
    # Regex patterns for finding styled lines and removing tags
    styling_tag_pattern = re.compile(r"<c(?:\.[^>]*)?>.*?</c>")
    remove_tags_pattern = re.compile(r"<[^>]+>")
    
    for raw_line in lines:
        # Only process lines with styling tags
        if not styling_tag_pattern.search(raw_line):
            continue
            
        # Remove all tags and strip whitespace
        clean = remove_tags_pattern.sub('', raw_line).strip()
        
        # Skip empty lines
        if not clean:
            continue
            
        # Skip duplicates
        if clean in seen:
            continue
            
        seen.add(clean)
        txt_lines.append(clean)
        
    return "\n\n".join(txt_lines)

def extract_vtt_to_txt(vtt_file_path: str, verbose: bool = False) -> str:
    """
    Convert a VTT file to TXT by extracting styled lines, removing tags, and saving as TXT.
    Deletes the original VTT file after successful conversion.
    
    Args:
        vtt_file_path (str): Path to the VTT file to convert
        verbose (bool, optional): Whether to log conversion steps. Defaults to False.
        
    Returns:
        str: Path to the created TXT file
        
    Raises:
        Exception: If file operations fail
    """
    try:
        log_event(f"Converting VTT to TXT: {vtt_file_path}", verbose)
        
        # Extract styled lines and remove tags
        txt_content = extract_styled_lines(vtt_file_path)
        
        # Create output path with .txt extension
        vtt_path = Path(vtt_file_path)
        txt_path = vtt_path.with_suffix('.txt')
        
        # Save the TXT file
        txt_path.write_text(txt_content, encoding='utf-8')
        log_event(f"Saved TXT file: {txt_path}", verbose)
        
        # Delete the original VTT file
        vtt_path.unlink()
        log_event(f"Deleted original VTT file: {vtt_file_path}", verbose)
        
        return str(txt_path)
        
    except Exception as e:
        log_event(f"[ERROR] Failed to convert VTT to TXT: {vtt_file_path} | {e}", verbose)
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m core.convertVTTtoTXT <vtt_file_path> [--verbose]")
        sys.exit(1)
        
    vtt_file = sys.argv[1]
    verbose = "--verbose" in sys.argv
    
    try:
        txt_file = extract_vtt_to_txt(vtt_file, verbose)
        print(f"Successfully converted {vtt_file} to {txt_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
