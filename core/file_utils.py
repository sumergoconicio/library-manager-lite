"""
core/file_utils.py | File Utility Module
Purpose: Utility functions for file operations (extension extraction, etc.)
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-23
Non-Std Deps: None
Abstract Spec: Contains reusable file utilities for use across modules.
"""

def get_file_extension(filename: str) -> str:
    """
    Purpose: Robustly extract the true file extension (after the last period) from a filename.
    Inputs: filename (str) - The full file name (with or without path).
    Outputs: extension (str) - The file extension, without the leading dot, or '' if none.
    Role: Ensures only the true extension is used, regardless of periods in the base name.
    """
    import os
    ext = os.path.splitext(filename)[1]
    return ext[1:] if ext.startswith('.') else ext
