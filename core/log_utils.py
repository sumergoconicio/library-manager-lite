"""
core/log_utils.py | Logging Utility for Verbose Mode
Author: ChAI-Engine
Last-Updated: 2025-05-25
Non-std deps: None
Abstract Spec: See dev/project-brief.md (T11)

Behavior: When --verbose is set, logs.txt is overwritten (not appended) at the start of each run. Only the latest operation is kept.
"""
from typing import Optional
from pathlib import Path

_log_file_initialized = {}
_default_log_path = None

def set_log_path(log_path: str):
    """
    Purpose: Set the default log file path for all log_event calls.
    Inputs: log_path (str)
    Outputs: None
    Role: Allows dynamic control of log location (e.g., catalog_folder/logs.txt).
    """
    global _default_log_path
    _default_log_path = log_path

def log_event(msg: str, verbose: bool, log_path: Optional[str] = None) -> None:
    """
    Purpose: Log a process event message to a file if verbose is True. On first call per run, overwrites logs.txt; subsequent calls append.
    Inputs:
        msg: Message to log (str)
        verbose: Whether to log (bool)
        log_path: Path to log file (Optional[str]); defaults to _default_log_path or 'core/logs.txt'.
    Outputs:
        None
    Role: Called by catalog workflow to record process steps for audit/debugging.
    Behavior: When --verbose is set, logs.txt is overwritten (not appended) at the start of each run. Only the latest operation is kept.
    """
    if not verbose:
        return
    global _default_log_path
    log_file = Path(log_path) if log_path else Path(_default_log_path) if _default_log_path else Path(__file__).parent / "logs.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    global _log_file_initialized
    key = str(log_file.resolve())
    mode = "a"
    if not _log_file_initialized.get(key, False):
        mode = "w"
        _log_file_initialized[key] = True
    with log_file.open(mode, encoding="utf-8") as f:
        f.write(msg.rstrip("\n") + "\n")
