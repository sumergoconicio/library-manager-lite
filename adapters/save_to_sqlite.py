"""
adapters/save_to_sqlite.py | SQLite Database Adapter
Purpose: Save dataframe from catalog_files.py to SQLite database alongside CSV files
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: pandas, sqlite3
Abstract Spec: Creates/updates SQLite database with catalog data in the same location as the CSV file. Implements efficient incremental updates by only modifying changed records. Logs each process iteration when verbose flag is set. Creates a backup of the database if --backupdb flag is set.
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
    backup_db: bool = False,
    force_new: bool = False
):
    """
    Purpose: Save pandas DataFrame to SQLite database with incremental updates
    Inputs:
        df (pd.DataFrame): DataFrame to save
        root (Path): Root directory path
        catalog_folder (str): Folder name for catalog files
        table_name (str): Name of the table in SQLite database
        verbose (bool): Enable verbose logging
        backup_db (bool): Create a backup of the database if True
        force_new (bool): Force creation of a new database, dropping existing data
    Outputs: None
    Role: Persists catalog data in SQLite format for querying and analysis with efficient incremental updates
    """
    catalog_dir = catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    db_path = catalog_dir / 'library.sqlite'
    
    log_event(f"[START] Saving DataFrame to SQLite database at {db_path}", verbose)
    start_time = time.time()
    
    try:
        # Create backup of the database if requested
        if backup_db and db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_filename = f"{timestamp}.library.sqlite.backup"
            backup_path = catalog_dir / backup_filename
            log_event(f"[STEP] Creating backup of SQLite database at {backup_path}", verbose)
            try:
                shutil.copy2(db_path, backup_path)
                log_event(f"[INFO] Database backup created successfully at {backup_path}", verbose)
            except Exception as e:
                log_event(f"[ERROR] Failed to create database backup: {e}", verbose)
        
        # Create connection to SQLite database
        log_event(f"[STEP] Creating connection to SQLite database", verbose)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Log DataFrame info before saving
        if verbose:
            row_count = len(df)
            col_count = len(df.columns)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_event(f"[INFO] DataFrame details: {row_count} rows, {col_count} columns at {timestamp}", verbose)
            log_event(f"[INFO] Columns: {', '.join(df.columns.tolist())}", verbose)
        
        # If force_new or table doesn't exist, create a new table
        if force_new:
            log_event(f"[STEP] Dropping existing table and creating new one", verbose)
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            
        # Check if table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Create table if it doesn't exist
            log_event(f"[STEP] Creating new table '{table_name}'", verbose)
            columns = [
                "relative_path TEXT", 
                "filename TEXT", 
                "extension TEXT", 
                "last_modified TEXT",
                "file_size_in_MB TEXT", 
                "textracted INTEGER", 
                "token_count TEXT",
                "sha256 TEXT",
                "PRIMARY KEY (relative_path, filename, extension)"
            ]
            cursor.execute(f"CREATE TABLE {table_name} ({', '.join(columns)})")
            conn.commit()
            
            # Insert all records
            log_event(f"[STEP] Inserting all records into new table", verbose)
            df['textracted'] = df['textracted'].astype(int)  # Convert boolean to int for SQLite
            df.to_sql(table_name, conn, if_exists='append', index=False)
        else:
            # Get existing records from database for comparison
            log_event(f"[STEP] Performing incremental update", verbose)
            
            # Get list of files to delete (files in DB but not in current scan)
            file_keys = set(zip(df['relative_path'], df['filename'], df['extension']))
            cursor.execute(f"SELECT relative_path, filename, extension FROM {table_name}")
            db_keys = set(cursor.fetchall())
            
            # Delete records for files that no longer exist
            keys_to_delete = db_keys - file_keys
            if keys_to_delete:
                log_event(f"[STEP] Deleting {len(keys_to_delete)} records for files that no longer exist", verbose)
                for key in keys_to_delete:
                    cursor.execute(
                        f"DELETE FROM {table_name} WHERE relative_path = ? AND filename = ? AND extension = ?",
                        key
                    )
            
            # Convert textracted to int for SQLite
            df['textracted'] = df['textracted'].astype(int)
            
            # Update or insert records
            log_event(f"[STEP] Updating or inserting {len(df)} records", verbose)
            for _, row in df.iterrows():
                # Check if this record exists
                cursor.execute(
                    f"SELECT last_modified FROM {table_name} WHERE relative_path = ? AND filename = ? AND extension = ?",
                    (row['relative_path'], row['filename'], row['extension'])
                )
                result = cursor.fetchone()
                
                if result:
                    # Update existing record
                    cursor.execute(
                        f"UPDATE {table_name} SET last_modified = ?, file_size_in_MB = ?, textracted = ?, token_count = ?, sha256 = ? "
                        f"WHERE relative_path = ? AND filename = ? AND extension = ?",
                        (
                            row['last_modified'], row['file_size_in_MB'], int(row['textracted']), 
                            row['token_count'], row['sha256'], row['relative_path'], 
                            row['filename'], row['extension']
                        )
                    )
                else:
                    # Insert new record
                    cursor.execute(
                        f"INSERT INTO {table_name} (relative_path, filename, extension, last_modified, file_size_in_MB, textracted, token_count, sha256) "
                        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            row['relative_path'], row['filename'], row['extension'], 
                            row['last_modified'], row['file_size_in_MB'], int(row['textracted']), 
                            row['token_count'], row['sha256']
                        )
                    )
        
        # Create indexes for faster querying
        log_event(f"[STEP] Creating indexes for faster querying", verbose)
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_extension ON {table_name} (extension)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_textracted ON {table_name} (textracted)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_filename ON {table_name} (filename)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_sha256 ON {table_name} (sha256)")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Calculate and log execution time
        execution_time = time.time() - start_time
        log_event(f"[END] SQLite database updated at {db_path} ({execution_time:.2f} seconds)", verbose)
    except Exception as e:
        log_event(f"[ERROR] Failed to save to SQLite database: {e}", verbose)
        # Print full exception for debugging
        import traceback
        log_event(traceback.format_exc(), verbose)
