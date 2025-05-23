"""
token_counter.py | TXT Token Counting Utility
Purpose: Estimate token count for a .txt file using tiktoken
Author: ChAI-Engine
Last-Updated: 2025-05-23
Non-Std Deps: tiktoken
Abstract Spec: Given a .txt file path, return the number of tokens in the file using tiktoken's encoding.
"""

def count_tokens(txt_file_path: str, encoding_name: str = "cl100k_base") -> int:
    """
    Purpose: Estimate the number of tokens in a TXT file using tiktoken.
    Inputs:
        txt_file_path (str): Path to the .txt file
        encoding_name (str): Name of tiktoken encoding to use (default: cl100k_base)
    Outputs:
        int: Token count
    Role: Utility function for cataloguing and workflow modules.
    """
    import tiktoken
    with open(txt_file_path, "r", encoding="utf-8") as f:
        text = f.read()
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    return len(tokens)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python token_counter.py <txt_file_path> [encoding_name]")
        sys.exit(1)
    txt_file = sys.argv[1]
    encoding = sys.argv[2] if len(sys.argv) > 2 else "cl100k_base"
    print(count_tokens(txt_file, encoding))
