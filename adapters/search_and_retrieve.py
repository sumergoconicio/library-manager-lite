"""
adapters/search_and_retrieve.py | Search Interface Adapter
Purpose: Receives semicolon-separated search terms (from agents/query_processor.py), processes and logs query, calls core search, returns and saves results.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-06
Non-Std Deps: pandas
Abstract Spec: Accepts search terms as input, processes and logs query, calls core search, returns results, and saves CSV in saved_searches_folder.
"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from core.sqlite_search import search_filenames
from core.log_utils import log_event, set_log_path


# get_search_query removed: user input is not part of new workflow


def process_query(search_query: str, verbose: bool = False) -> str | list:
    """
    Purpose: Process and sanitize the search query
    Inputs:
        search_query (str): The raw search query from user
        verbose (bool): Enable verbose logging
    Outputs:
        processed_query (str): The processed search query
    Role: Ensure search query is properly formatted for database search
    """
    # Check for semicolon-separated multi-term search
    if ';' in search_query:
        terms = [term.strip() for term in search_query.split(';')]
        processed_terms = [term for term in terms if term]
        if verbose:
            log_event(f"[STEP] Processing multi-term search query: '{search_query}' -> {processed_terms}", verbose)
        return processed_terms
    else:
        processed_query = search_query.strip()
        if verbose:
            log_event(f"[STEP] Processing single-term search query: '{search_query}' -> '{processed_query}'", verbose)
        return processed_query


def display_results(results: list) -> None:
    """
    Purpose: Format and display search results to the user
    Inputs:
        results (list): List of dictionaries with file information
    Outputs: None (prints to console)
    Role: User-friendly presentation of search results
    """
    if not results:
        print("\nNo files found matching your search term.")
        return
    
    print(f"\nFound {len(results)} matching files:")
    print("=" * 80)
    
    # Group results by top-level folder (first part of relative_path)
    grouped_results = {}
    for item in results:
        rel_path = item['relative_path']
        parts = rel_path.split('/')
        top_level = parts[0] if parts else "Root"
        
        if top_level not in grouped_results:
            grouped_results[top_level] = []
        
        grouped_results[top_level].append(item)
    
    # Display results grouped by top-level folder
    for folder, items in sorted(grouped_results.items()):
        print(f"\n[{folder}]")
        print("-" * 80)
        
        for item in sorted(items, key=lambda x: x['filename']):
            filename = item['filename']
            extension = item['extension']
            size = f"{item['file_size_in_MB']:.2f} MB" if item['file_size_in_MB'] else "N/A"
            
            # Format the full path (excluding the top-level folder which is already shown)
            path_parts = item['relative_path'].split('/')
            sub_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ""
            
            if sub_path:
                print(f"  {filename}.{extension} ({size}) - {sub_path}")
            else:
                print(f"  {filename}.{extension} ({size})")
    
    print("\n" + "=" * 80)


def save_results_to_csv(results: list, search_query: str | list, saved_searches_folder: Path, verbose: bool = False) -> None:
    """
    Purpose: Save search results to a CSV file
    Inputs:
        results (list): List of dictionaries with file information
        search_query (str): The search query used
        saved_searches_folder (Path): Path to the folder where CSV should be saved
        verbose (bool): Enable verbose logging
    Outputs: None
    Role: Persist search results for future reference
    """
    if not results:
        log_event(f"[INFO] No results to save for query: '{search_query}'", verbose)
        return
    
    # Create the saved_searches_folder if it doesn't exist
    saved_searches_folder.mkdir(parents=True, exist_ok=True)
    
    # Format the filename with timestamp and search query
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    if isinstance(search_query, list):
        safe_query = '_'.join(search_query)
    else:
        safe_query = search_query
    safe_query = safe_query.replace(' ', '_').replace('/', '_').replace('\\', '_')
    safe_query = ''.join(c for c in safe_query if c.isalnum() or c == '_')
    filename = f"{timestamp}_{safe_query}.csv"
    filepath = saved_searches_folder / filename
    
    # Prepare data for CSV
    csv_data = []
    for item in results:
        # Extract top-level folder from relative_path
        rel_path = item['relative_path']
        parts = rel_path.split('/')
        top_level = parts[0] if parts else "Root"
        
        # Format the filename with extension
        full_filename = f"{item['filename']}.{item['extension']}"
        
        csv_data.append({
            'top_level_folder': top_level,
            'filename': full_filename
        })
    
    # Sort data by top_level_folder and filename
    csv_data.sort(key=lambda x: (x['top_level_folder'], x['filename']))
    
    # Write to CSV
    try:
        df = pd.DataFrame(csv_data)
        df.to_csv(filepath, index=False)
        log_event(f"[INFO] Search results saved to {filepath}", verbose)
        print(f"\nSearch results saved to: {filepath}")
    except Exception as e:
        log_event(f"[ERROR] Failed to save search results: {e}", verbose)
        print(f"\nError saving search results: {e}")


def run_search(profile_config: dict, search_terms: str, verbose: bool = False) -> list:
    """
    Purpose: Main entry point for search functionality (no user prompt)
    Inputs:
        profile_config (dict): Configuration from the active profile
        search_terms (str): Semicolon-separated search terms (from query_processor)
        verbose (bool): Enable verbose logging
    Outputs: list of results (dicts with top_level_folder, filename)
    Role: Process search_terms, log steps, call core search, return and save results
    """
    catalog_folder = Path(profile_config['catalog_folder'])
    log_path = catalog_folder / 'logs.txt'
    # Ensure default log path is set so downstream modules log to the correct file
    set_log_path(str(log_path))

    saved_searches_folder = None
    if profile_config.get('saved_searches_folder'):
        saved_searches_folder = Path(profile_config['saved_searches_folder'])

    # Process the query (single or multi-term)
    processed_query = process_query(search_terms, verbose)

    # Log processing step and final query if verbose
    if verbose:
        log_event(f"[STEP] Received search_terms: '{search_terms}'", verbose, log_path)
        log_event(f"[STEP] Processed query: '{processed_query}'", verbose, log_path)

    # Search the database
    results = search_filenames(catalog_folder, processed_query, verbose)
    # Filter to only include .txt files
    results = [item for item in results if item.get('extension', '').lower() == 'txt']
    # Prepare return: list of dicts with top_level_folder, filename
    output_list = []
    for idx, item in enumerate(results):
        if 'relative_path' not in item:
            continue
        rel_path = item['relative_path']
        parts = rel_path.split('/')
        top_level = parts[0] if parts else "Root"
        full_filename = f"{item.get('filename', '[missing]')}.{item.get('extension', '[missing]')}"
        output_list.append({
            'top_level_folder': top_level,
            'filename': full_filename
        })
    # Sort output
    output_list.sort(key=lambda x: (x['top_level_folder'], x['filename']))

    # Save results to CSV if folder is configured
    if saved_searches_folder:
        save_results_to_csv(results, processed_query, saved_searches_folder, verbose)

    # Clean, grouped display by top_level_folder
    if output_list:
        grouped = {}
        for row in output_list:
            folder = row['top_level_folder']
            grouped.setdefault(folder, []).append(row['filename'])
        for folder in sorted(grouped.keys()):
            print(f"{folder}\n{'-' * 16}")
            for filename in sorted(grouped[folder]):
                print(filename)
            print()  # Blank line between folders
    return output_list


# --- Interactive Search Workflow ---

def interactive_search(args):
    """
    Purpose: End-to-end interactive search workflow triggered from main.py.
    Inputs:
        args (argparse.Namespace): Parsed CLI arguments providing verbosity flag and profile selection.
                                  May contain user_query attribute if provided externally.
    Outputs:
        list: Search results returned by `run_search` (list of dicts with top_level_folder and filename).
    Role: Handles user prompting, keyword extraction via `agents/query_processor.py`, loads profile configuration,
          delegates database search to `run_search`, and returns the results. Keeps `main.py` lean by
          encapsulating all search logic within the adapter layer.
    """
    # Local (lazy) imports to avoid unnecessary dependencies at module import time
    import subprocess
    import sys
    from pathlib import Path
    from ports.profile_loader import load_profile_config

    # Check if user query was provided externally (e.g., from book_recommender)
    if hasattr(args, 'user_query') and args.user_query:
        user_query = args.user_query
    else:
        # Prompt user for natural-language query
        user_query = input("What topic are you researching today? ").strip()
        if not user_query:
            print("[ERROR] Search query cannot be empty.")
            sys.exit(1)

    if getattr(args, "verbose", False):
        log_event(f"[DEBUG] User query: {user_query}", True)

    # Derive keyword search terms using the LLM-powered query processor
    project_root = Path(__file__).parent.parent
    query_proc_path = project_root / "agents" / "query_processor.py"
    if not query_proc_path.exists():
        print(f"[ERROR] Query processor not found at {query_proc_path}")
        sys.exit(1)

    try:
        result = subprocess.run(
            [sys.executable, str(query_proc_path), user_query],
            capture_output=True,
            text=True,
            check=True,
        )
        search_terms = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Query processor failed: {e.stderr}")
        sys.exit(1)

    if getattr(args, "verbose", False):
        log_event(f"[DEBUG] Extracted search keywords: {search_terms}", True)

    if not search_terms:
        print("[ERROR] No keywords extracted from your query. Please try a different search.")
        sys.exit(1)

    # Load profile-specific configuration
    profile_config = load_profile_config(args=args)

    # Delegate actual filename search to existing helper
    results = run_search(profile_config, search_terms, verbose=getattr(args, "verbose", False))

    return results
