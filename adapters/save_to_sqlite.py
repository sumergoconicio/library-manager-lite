"""
adapters/save_to_sqlite.py | SQLite Database Adapter
Purpose: Save dataframe from catalog_files.py to SQLite database alongside CSV files
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-04
Non-Std Deps: pandas, sqlite3
Abstract Spec: Creates/updates SQLite database with catalog data in the same location as the CSV file.
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path
from core.log_utils import log_event


def save_dataframe_to_sqlite(
    df: pd.DataFrame, 
    root: Path, 
    catalog_folder: str, 
    table_name: str = "catalog", 
    verbose: bool = False
):
    """
    Purpose: Save pandas DataFrame to SQLite database
    Inputs:
        df (pd.DataFrame): DataFrame to save
        root (Path): Root directory path
        catalog_folder (str): Folder name for catalog files
        table_name (str): Name of the table in SQLite database
        verbose (bool): Enable verbose logging
    Outputs: None
    Role: Persists catalog data in SQLite format for querying and analysis
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    db_path = catalog_dir / 'library.sqlite'
    
    try:
        # Create connection to SQLite database
        conn = sqlite3.connect(str(db_path))
        
        # Write DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Close connection
        conn.close()
        
        log_event(f"SQLite database updated at {db_path}", verbose)
    except Exception as e:
        log_event(f"[ERROR] Failed to save to SQLite database: {e}", verbose)
