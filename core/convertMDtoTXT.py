"""
core/convertMDtoTXT.py
Markdown-to-TXT Conversion Utility
Author: ChAI-Engine
Last-Updated: 2025-05-23
Non-Std Deps: None
Abstract Spec: Accept a single MD file path, extract the filename, and save a copy as .txt in the same directory.
"""

def convert_md_to_txt(md_path: str) -> str:
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
    if not md_path.lower().endswith('.md'):
        raise ValueError('Input file must have .md extension')
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f'File not found: {md_path}')
    txt_path = os.path.splitext(md_path)[0] + '.txt'
    shutil.copyfile(md_path, txt_path)
    return txt_path

def main():
    """
    Purpose: CLI entry point for Markdown-to-TXT conversion.
    Inputs: Command-line argument: path to .md file
    Outputs: Prints the path to the .txt file created
    Role: Entry point for manual or scripted invocation.
    """
    import sys
    if len(sys.argv) != 2:
        print('Usage: python core/convertMDtoTXT.py <path-to-md-file>')
        sys.exit(1)
    md_path = sys.argv[1]
    try:
        txt_path = convert_md_to_txt(md_path)
        print(f'Success: {txt_path}')
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
