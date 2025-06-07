"""
Title: Book Recommender
Description: Recommends books based on search results and user's research query using LLM.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: pandas, adapters.llm_provider, python-dotenv
Abstract Spec: Builds on search workflow to provide curated book recommendations.
"""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import glob

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
    from adapters.search_and_retrieve import interactive_search
except ModuleNotFoundError as e:
    print("\n[ImportError] Could not import required modules.\n"
          "Make sure you are running this script from the project root, "
          "or that the library-manager-lite directory is in your PYTHONPATH.\n"
          f"Original error: {e}")
    sys.exit(1)


def get_latest_search_results(saved_searches_folder: Path) -> Path:
    """
    Purpose: Find the most recent search results CSV file
    Inputs:
        saved_searches_folder (Path): Path to the folder containing saved search results
    Outputs:
        Path: Path to the most recent search results CSV file
    Role: Locate the latest search results for recommendation processing
    """
    if not saved_searches_folder.exists():
        print(f"[ERROR] Saved searches folder not found: {saved_searches_folder}")
        sys.exit(1)
        
    # Get all CSV files in the saved searches folder
    csv_files = list(saved_searches_folder.glob("*.csv"))
    
    if not csv_files:
        print("[ERROR] No search results found. Please run a search first.")
        sys.exit(1)
        
    # Sort by modification time (newest first)
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    return latest_file


def generate_recommendations(user_query: str, search_results_path: Path, verbose: bool = False) -> str:
    """
    Purpose: Generate book recommendations using LLM based on search results and user query
    Inputs:
        user_query (str): The user's research query
        search_results_path (Path): Path to the search results CSV file
        verbose (bool): Enable verbose logging
    Outputs:
        str: Formatted book recommendations
    Role: Core recommendation generation logic
    """
    # Load system prompt
    prompt_path = Path(__file__).parent / "book_recommender_prompt.txt"
    if not prompt_path.exists():
        print(f"[ERROR] System prompt file not found: {prompt_path}")
        sys.exit(1)
    system_prompt = load_prompt(str(prompt_path))
    
    # Load search results
    try:
        search_results = pd.read_csv(search_results_path)
    except Exception as e:
        print(f"[ERROR] Failed to load search results: {e}")
        sys.exit(1)
        
    # Prepare search results as a formatted string for the LLM
    csv_content = search_results.to_string(index=False)
    
    # Get LLM provider for this workflow
    try:
        provider = get_llm_provider(workflow="book_recommender")
    except Exception:
        provider = get_llm_provider()
        
    # Call LLM to generate recommendations
    try:
        user_message = f"""
Research Query: {user_query}

Search Results CSV:
{csv_content}
"""
        response = provider.completion(system_prompt, user_message, output_format="text")
        return response.strip()
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}", file=sys.stderr)
        sys.exit(1)


def main(args=None, user_query=None):
    """
    Purpose: Entry point for book recommender. Runs search workflow, then generates recommendations.
    Inputs: 
        args (argparse.Namespace) - Command line arguments from main.py
        user_query (str) - Optional pre-provided user query
    Outputs: Formatted book recommendations (stdout)
    Role: Orchestrates search and recommendation workflow
    """
    # If called directly (not from main.py), parse arguments
    if args is None:
        import argparse
        parser = argparse.ArgumentParser(description="Book recommendation system based on search results")
        parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
        parser.add_argument("--profile", type=str, default=None, help="Profile to use from folder_paths.json")
        parser.add_argument("query", nargs="?", type=str, help="Research query (optional)")
        args = parser.parse_args()
        if hasattr(args, 'query') and args.query:
            user_query = args.query
    
    # Prompt user for research query if not provided
    if user_query is None:
        user_query = input("What topic are you researching today? ").strip()
        if not user_query:
            print("[ERROR] Research query cannot be empty.")
            sys.exit(1)
        
    # Run the search workflow to generate search results
    print(f"\n[STEP 1] Running search for: '{user_query}'...")
    # Create a custom args object with the user_query attribute
    from types import SimpleNamespace
    search_args = SimpleNamespace(**vars(args))
    search_args.user_query = user_query
    search_results = interactive_search(search_args)
    
    if not search_results:
        print("[ERROR] No search results found. Cannot generate recommendations.")
        sys.exit(1)
        
    # Load profile-specific configuration
    from ports.profile_loader import load_profile_config
    profile_config = load_profile_config(args=args)
    
    # Get saved searches folder path
    saved_searches_folder = Path(profile_config.get("saved_searches_folder", ""))
    if not saved_searches_folder:
        print("[ERROR] No saved_searches_folder configured in profile.")
        sys.exit(1)
    
    # Get the latest search results file
    latest_search_file = get_latest_search_results(saved_searches_folder)
    print(f"\n[STEP 2] Using search results from: {latest_search_file.name}")
    
    # Generate recommendations
    print("\n[STEP 3] Generating book recommendations...")
    recommendations = generate_recommendations(user_query, latest_search_file, verbose=args.verbose)
    
    # Display recommendations
    print("\n" + "=" * 80)
    print("BOOK RECOMMENDATIONS")
    print("=" * 80)
    print(recommendations)
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
