"""
adapters/search_and_retrieve.py | Search Interface Adapter
Purpose: Handle user interaction for search functionality and display results
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-06
Non-Std Deps: None
Abstract Spec: Prompts user for search query, processes input, calls core search function,
              and formats results for display to the user.
"""

import os
from pathlib import Path
from core.sqlite_search import search_filenames
from core.log_utils import log_event


def get_search_query() -> str:
    """
    Purpose: Prompt user for a search term
    Inputs: None
    Outputs: search_query (str): The user's search term
    Role: User interaction for search functionality
    """
    print("\nLibrary Manager Search")
    print("=====================")
    search_query = input("Enter search term: ")
    return search_query


def process_query(search_query: str, verbose: bool = False) -> str:
    """
    Purpose: Process and sanitize the search query
    Inputs:
        search_query (str): The raw search query from user
        verbose (bool): Enable verbose logging
    Outputs:
        processed_query (str): The processed search query
    Role: Ensure search query is properly formatted for database search
    """
    # Remove leading/trailing whitespace
    processed_query = search_query.strip()
    
    if verbose:
        log_event(f"[STEP] Processing search query: '{search_query}' -> '{processed_query}'", verbose)
    
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


def run_search(profile_config: dict, verbose: bool = False) -> None:
    """
    Purpose: Main entry point for search functionality
    Inputs:
        profile_config (dict): Configuration from the active profile
        verbose (bool): Enable verbose logging
    Outputs: None
    Role: Orchestrate the search workflow
    """
    # Get paths from profile config
    catalog_folder = Path(profile_config['catalog_folder'])
    log_path = catalog_folder / 'logs.txt'
    
    # Get search query from user
    search_query = get_search_query()
    
    # Process the query
    processed_query = process_query(search_query, verbose)
    
    # Log the search query if verbose
    if verbose:
        log_event(f"[INFO] Search query: '{processed_query}'", verbose)
    
    # Search the database
    results = search_filenames(catalog_folder, processed_query, verbose)
    
    # Display results to the user
    display_results(results)
