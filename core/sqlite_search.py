"""
core/sqlite_search.py | SQLite Search Module
Purpose: Search the SQLite database for filenames matching a search query
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-06
Non-Std Deps: sqlite3
Abstract Spec: Connects to SQLite database, performs search queries on filename field, 
              and returns results as a list of dictionaries with file information.
"""

import sqlite3
from pathlib import Path
import os
from core.log_utils import log_event


def search_filenames(
    catalog_folder: Path, 
    search_query: str, 
    verbose: bool = False
) -> list:
    """
    Purpose: Search SQLite database for filenames containing the search query
    Inputs:
        catalog_folder (Path): Path to the folder containing the SQLite database
        search_query (str): The search term to look for in filenames
        verbose (bool): Enable verbose logging
    Outputs:
        results (list): List of dictionaries with file information
    Role: Core search functionality for the library manager
    """
    log_event(f"[START] Searching for files with query: '{search_query}'", verbose)
    
    db_path = catalog_folder / 'library.sqlite'
    
    if not os.path.exists(db_path):
        log_event(f"[ERROR] SQLite database not found at {db_path}", verbose)
        return []
    
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Use parameterized query to avoid SQL injection
        search_pattern = f"%{search_query}%"
        query = """
            SELECT relative_path, filename, extension, last_modified, file_size_in_MB
            FROM catalog
            WHERE filename LIKE ?
            ORDER BY relative_path, filename
        """
        
        log_event(f"[STEP] Executing SQL query with pattern: '{search_pattern}'", verbose)
        cursor.execute(query, (search_pattern,))
        
        # Fetch all matching rows
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries for easier handling
        results = []
        for row in rows:
            results.append({
                'relative_path': row[0],
                'filename': row[1],
                'extension': row[2],
                'last_modified': row[3],
                'file_size_in_MB': row[4]
            })
        
        # Close the connection
        conn.close()
        
        log_event(f"[END] Search complete. Found {len(results)} matching files.", verbose)
        return results
        
    except Exception as e:
        log_event(f"[ERROR] Error searching database: {e}", verbose)
        return []
