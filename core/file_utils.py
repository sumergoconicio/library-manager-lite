"""
core/file_utils.py | File Utility Module
Purpose: Utility functions for file operations (extension extraction, config/prompt loading, etc.)
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-25
Non-Std Deps: None
Abstract Spec: Contains reusable file utilities for use across modules, including config and prompt loading with error handling.
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


def load_config(config_path, required_keys=None):
    """
    Purpose: Load a JSON config file and validate required keys.
    Inputs: config_path (Path or str) - Path to the config file.
            required_keys (list or None) - List of required keys to check.
    Outputs: config (dict) - Loaded configuration dictionary.
    Role: Centralizes config loading and validation with error handling.
    """
    import json
    from pathlib import Path
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"[ERROR] Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    if required_keys:
        for key in required_keys:
            if key not in config:
                raise KeyError(f"[ERROR] Required key '{key}' not found in {config_path}")
    return config


def load_prompt(prompt_path):
    """
    Purpose: Load a prompt text file for LLM workflows.
    Inputs: prompt_path (Path or str) - Path to the prompt file.
    Outputs: prompt (str) - Prompt file contents as string.
    Role: Centralizes prompt file loading with error handling.
    """
    from pathlib import Path
    prompt_path = Path(prompt_path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"[ERROR] Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")

