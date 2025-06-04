"""
adapters/save_to_sqlite.py | SQLite Database Adapter
Purpose: Save dataframe from catalog_files.py to SQLite database alongside CSV files
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-04
Non-Std Deps: pandas, sqlite3
Abstract Spec: Creates/updates SQLite database with catalog data in the same location as the CSV file. Logs each process iteration when verbose flag is set. Creates a backup of the database if --backupdb flag is set.
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path
from core.log_utils import log_event
import time
import shutil
from datetime import datetime


def save_dataframe_to_sqlite(
    df: pd.DataFrame, 
    root: Path, 
    catalog_folder: str, 
    table_name: str = "catalog", 
    verbose: bool = False,
    backup_db: bool = False
):
    """
    Purpose: Save pandas DataFrame to SQLite database
    Inputs:
        df (pd.DataFrame): DataFrame to save
        root (Path): Root directory path
        catalog_folder (str): Folder name for catalog files
        table_name (str): Name of the table in SQLite database
        verbose (bool): Enable verbose logging
        backup_db (bool): Create a backup of the database if True
    Outputs: None
    Role: Persists catalog data in SQLite format for querying and analysis
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    db_path = catalog_dir / 'library.sqlite'
    
    log_event(f"[START] Saving DataFrame to SQLite database at {db_path}", verbose)
    start_time = time.time()
    
    try:
        # Create connection to SQLite database
        log_event(f"[STEP] Creating connection to SQLite database", verbose)
        conn = sqlite3.connect(str(db_path))
        
        # Log DataFrame info before saving
        if verbose:
            row_count = len(df)
            col_count = len(df.columns)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_event(f"[INFO] DataFrame details: {row_count} rows, {col_count} columns at {timestamp}", verbose)
            log_event(f"[INFO] Columns: {', '.join(df.columns.tolist())}", verbose)
        
        # Write DataFrame to SQLite
        log_event(f"[STEP] Writing DataFrame to '{table_name}' table", verbose)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Create indexes for faster querying if needed
        log_event(f"[STEP] Creating indexes for faster querying", verbose)
        cursor = conn.cursor()
        # Index on commonly queried columns
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_extension ON {table_name} (extension)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_textracted ON {table_name} (textracted)")
        conn.commit()
        
        # Close connection
        log_event(f"[STEP] Closing database connection", verbose)
        conn.close()
        
        # Create a backup of the database if requested
        if backup_db:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_filename = f"{timestamp}.library.sqlite.backup"
            backup_path = catalog_dir / backup_filename
            log_event(f"[STEP] Creating backup of SQLite database at {backup_path}", verbose)
            try:
                shutil.copy2(db_path, backup_path)
                log_event(f"[INFO] Database backup created successfully at {backup_path}", verbose)
            except Exception as e:
                log_event(f"[ERROR] Failed to create database backup: {e}", verbose)
        
        # Calculate and log execution time
        execution_time = time.time() - start_time
        log_event(f"[END] SQLite database updated at {db_path} ({execution_time:.2f} seconds)", verbose)
    except Exception as e:
        log_event(f"[ERROR] Failed to save to SQLite database: {e}", verbose)
