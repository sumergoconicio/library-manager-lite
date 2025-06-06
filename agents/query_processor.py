"""
Title: Query Processor
Description: Prompts user for research topic, extracts semicolon-separated keywords using LLM, and passes to search adapter.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-06
Non-Std Deps: adapters.llm_provider, python-dotenv
Abstract Spec: See dev/project-brief.md Sprint 35
"""

import sys
from pathlib import Path

# Load .env file from project root for environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    print("[Warning] python-dotenv not installed. If you use a .env file for secrets, install with: pip install python-dotenv")

# Ensure project root is in sys.path for absolute imports
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from adapters.llm_provider import get_llm_provider
    from core.file_utils import load_prompt, load_config
except ModuleNotFoundError as e:
    print("\n[ImportError] Could not import required modules.\n"
          "Make sure you are running this script from the project root, "
          "or that the library-manager-lite directory is in your PYTHONPATH.\n"
          f"Original error: {e}")
    sys.exit(1)

# prompt_user removed: user query is now passed as a CLI argument

def main():
    """
    Purpose: Entry point for query processor. Loads config, system prompt, receives user query as CLI arg, calls LLM, prints keywords.
    Inputs: CLI arg (user_query)
    Outputs: Semicolon-separated keywords (stdout)
    Role: Orchestrates LLM call and output
    """
    import argparse
    parser = argparse.ArgumentParser(description="LLM keyword extractor for search workflow")
    parser.add_argument("user_query", type=str, help="User's natural language search query")
    args = parser.parse_args()
    user_query = args.user_query.strip()
    current_research_query = user_query

    # Load config/profile
    config_path = Path(__file__).resolve().parent.parent / "user_inputs" / "folder_paths.json"
    config = load_config(str(config_path))

    # Load system prompt
    prompt_path = Path(__file__).parent / "query_processor_prompt.txt"
    if not prompt_path.exists():
        print(f"System prompt file not found: {prompt_path}")
        sys.exit(1)
    system_prompt = load_prompt(str(prompt_path))

    # Get LLM provider for this workflow
    try:
        provider = get_llm_provider(workflow="search_query")
    except Exception:
        provider = get_llm_provider()

    # Call LLM to extract keywords
    try:
        response = provider.completion(system_prompt, user_query, output_format="text")
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Output semicolon-separated keywords
    print(response.strip())

if __name__ == "__main__":
    main()
