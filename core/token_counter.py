"""
token_counter.py | TXT Token Counting Utility
Purpose: Estimate token count for a .txt file using model-agnostic heuristics
Author: ChAI-Engine
Last-Updated: 2025-05-24
Non-Std Deps: None
Abstract Spec: Given a .txt file path, return the estimated number of tokens using two heuristics and their average.
"""

from core.log_utils import log_event

def count_tokens(txt_file_path: str, verbose: bool = False) -> int:
    """
    Purpose: Estimate the number of tokens in a TXT file using model-agnostic heuristics.
    Inputs:
        txt_file_path (str): Path to the .txt file
    Outputs:
        int: Estimated token count
    Role: Utility function for cataloguing and workflow modules.
    Heuristics:
        - est1: len(text.split()) * 1.25 (word count, ~30% underestimate)
        - est2: (len(text) / 4) * 0.75 (character count, ~25% overestimate)
        - Average of both as final token_count
    """
    log_event(f"[INFO] Counting tokens in {txt_file_path}", verbose)
    with open(txt_file_path, "r", encoding="utf-8") as f:
        text = f.read()
    est1_token_count = len(text.split()) * 1.25
    est2_token_count = (len(text) / 4) * 0.75
    token_count = int((est1_token_count + est2_token_count) / 2)
    log_event(f"[INFO] Token count for {txt_file_path}: {token_count}", verbose)
    return token_count

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python token_counter.py <txt_file_path>")
        sys.exit(1)
    txt_file = sys.argv[1]
    print(count_tokens(txt_file))
