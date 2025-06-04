"""
ports/convertMDtoTXT.py
Markdown-to-TXT Conversion Utility
Author: ChAI-Engine
Last-Updated: 2025-06-04
Non-Std Deps: None
Abstract Spec: Accept a single MD file path, extract the filename, and save a copy as .txt in the same directory.
"""

from core.log_utils import log_event

def convert_md_to_txt(md_path: str, verbose: bool = False) -> str:
    """
    Purpose: Convert a Markdown (.md) file to a plain text (.txt) file by copying content and renaming the extension.
    Inputs:
        md_path (str): Path to the input Markdown (.md) file.
    Outputs:
        str: Path to the output TXT file.
    Role: Core adapter for Markdown-to-TXT conversion.
    """
    import os
    import shutil
    log_event(f"[INFO] Starting MD→TXT conversion: {md_path}", verbose)
    if not md_path.lower().endswith('.md'):
        log_event(f"[ERROR] Input file must have .md extension: {md_path}", verbose)
        raise ValueError('Input file must have .md extension')
    if not os.path.isfile(md_path):
        log_event(f"[ERROR] File not found: {md_path}", verbose)
        raise FileNotFoundError(f'File not found: {md_path}')
    txt_path = os.path.splitext(md_path)[0] + '.txt'
    shutil.copyfile(md_path, txt_path)
    log_event(f"[INFO] Created TXT: {txt_path}", verbose)
    return txt_path

def main(verbose: bool = False):
    """
    Purpose: CLI entry point for Markdown-to-TXT conversion.
    Inputs: Command-line argument: path to .md file
    Outputs: Prints the path to the .txt file created
    Role: Entry point for manual or scripted invocation.
    """
    import sys
    if len(sys.argv) != 2:
        log_event('Usage: python ports/convertMDtoTXT.py <path-to-md-file>', verbose)
        print('Usage: python ports/convertMDtoTXT.py <path-to-md-file>')
        sys.exit(1)
    md_path = sys.argv[1]
    try:
        txt_path = convert_md_to_txt(md_path, verbose=verbose)
        log_event(f'Success: {txt_path}', verbose)
        print(f'Success: {txt_path}')
    except Exception as e:
        log_event(f'Error: {e}', verbose)
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
