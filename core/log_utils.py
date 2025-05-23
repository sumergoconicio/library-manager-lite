"""
core/log_utils.py | Logging Utility for Verbose Mode
Author: ChAI-Engine
Last-Updated: 2025-05-24
Non-std deps: None
Abstract Spec: See dev/project-brief.md (T11)
"""
from typing import Optional
from pathlib import Path

def log_event(msg: str, verbose: bool, log_path: Optional[str] = None) -> None:
    """
    Purpose: Log a process event message to a file if verbose is True.
    Inputs:
        msg: Message to log (str)
        verbose: Whether to log (bool)
        log_path: Path to log file (Optional[str]); defaults to 'core/logs.txt'.
    Outputs:
        None
    Role: Called by catalog workflow to record process steps for audit/debugging.
    """
    if not verbose:
        return
    log_file = Path(log_path) if log_path else Path(__file__).parent / "logs.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(msg.rstrip("\n") + "\n")
