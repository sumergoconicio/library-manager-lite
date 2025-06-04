"""
catalog_analyzer.py | Catalog Analysis Module
Purpose: Analyze catalog data from SQLite for file/folder/extension/token statistics and output summary as CSV files.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-04
Non-Std Deps: pandas, sqlite3
Abstract Spec: Loads catalog data from SQLite, computes summary statistics (files/textracted/tokens per folder with totals, extensions with totals, textracted files, token counts), outputs tables as separate CSV files (latest-folder-breakdown.csv, latest-extension-breakdown.csv).
"""

import sqlite3
from pathlib import Path
import pandas as pd
import json
from core.log_utils import log_event

def load_catalog_from_sqlite(db_path: Path, verbose: bool = False) -> pd.DataFrame:
    """
    Purpose: Load catalog data from SQLite database
    Inputs: db_path (Path), verbose (bool)
    Outputs: DataFrame containing catalog data
    Role: Provides data access layer for SQLite database
    """
    try:
        conn = sqlite3.connect(str(db_path))
        query = "SELECT * FROM catalog"
        df = pd.read_sql_query(query, conn)
        conn.close()
        log_event(f"[INFO] Successfully loaded catalog data from SQLite: {db_path}", verbose)
        return df
    except Exception as e:
        log_event(f"[ERROR] Failed to load from SQLite database: {e}", verbose)
        return None

def analyze_catalog(output_mode="csv", verbose: bool = False):
    """
    Purpose: Analyze catalog data from SQLite and output summary tables as separate CSV files.
    Inputs: 
        output_mode (str: 'print', 'return', or 'csv')
        verbose (bool): Enable verbose logging
    Outputs: None or dict of tables
    Role: Loads config, resolves catalog path, computes file/folder/ext/token stats with totals, counts textracted files, 
          writes separate CSV files for folder breakdown and extension breakdown.
    """
    log_event("[INFO] Starting catalog analysis", verbose)
    config_path = Path("user_inputs/folder_paths.json")
    if not config_path.exists():
        log_event(f"[ERROR] Config file not found: {config_path}", verbose)
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        config = json.load(f)
    root_folder = config.get("root_folder_path")
    catalog_folder = config.get("catalog_folder", "_catalog")
    if not root_folder:
        log_event("[ERROR] root_folder_path must be set in user_inputs/folder-paths.json", verbose)
        raise ValueError("root_folder_path must be set in user_inputs/folder-paths.json")
    
    # Define paths for catalog files
    sqlite_path = Path(root_folder) / catalog_folder / "library.sqlite"
    
    # Define paths for the separate CSV files
    folder_breakdown_path = Path(root_folder) / catalog_folder / "latest-folder-breakdown.csv"
    extension_breakdown_path = Path(root_folder) / catalog_folder / "latest-extension-breakdown.csv"
    
    # Load from SQLite database
    if not sqlite_path.exists():
        log_event(f"[ERROR] SQLite database not found: {sqlite_path}", verbose)
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    
    df = load_catalog_from_sqlite(sqlite_path, verbose)
    if df is None:
        log_event(f"[ERROR] Failed to load data from SQLite database", verbose)
        raise RuntimeError("Failed to load data from SQLite database")
    # Check required columns
    required_cols = ["relative_path", "extension"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        log_event(f"[ERROR] Missing required columns in catalog: {missing}. Available columns: {list(df.columns)}", verbose)
        raise KeyError(f"Missing required columns in catalog: {missing}. Available columns: {list(df.columns)}")
    
    # Extract top-level folder from relative_path
    df['top_folder'] = df['relative_path'].apply(lambda x: Path(x).parts[0] if Path(x).parts else 'unknown')
    
    # Ensure textracted column exists and is properly formatted
    if 'textracted' not in df.columns:
        df['textracted'] = False
    else:
        df['textracted'] = df['textracted'].fillna(False).astype(bool)
    
    # Ensure token_count column exists and is properly formatted
    if 'token_count' not in df.columns:
        df['token_count'] = 0
    else:
        df['token_count'] = pd.to_numeric(df['token_count'], errors='coerce').fillna(0)
    
    # Ensure file_size_in_MB column exists and is properly formatted
    if 'file_size_in_MB' not in df.columns:
        df['file_size_in_MB'] = 0
    else:
        df['file_size_in_MB'] = pd.to_numeric(df['file_size_in_MB'], errors='coerce').fillna(0)
    
    # Count files, textracted files, file_size_in_MB, and token count per top-level folder
    folder_stats = df.groupby('top_folder').agg(
        file_count=('relative_path', 'count'),
        textracted_count=('textracted', lambda x: x.sum()),
        file_size_MB=('file_size_in_MB', 'sum'),
        token_count=('token_count', 'sum')
    ).reset_index()
    
    # Format file_size_MB to max 3 decimal places
    folder_stats['file_size_MB'] = folder_stats['file_size_MB'].round(3)
    
    # Add total row to folder_stats
    total_files = folder_stats['file_count'].sum()
    total_textracted = folder_stats['textracted_count'].sum()
    total_file_size = round(folder_stats['file_size_MB'].sum(), 3)  # Round total to 3 decimal places
    total_tokens = folder_stats['token_count'].sum()
    folder_stats.loc[len(folder_stats)] = ['TOTAL', total_files, total_textracted, total_file_size, total_tokens]
    
    # Count unique extension types
    ext_counts = df['extension'].value_counts().reset_index()
    ext_counts.columns = ['extension', 'file_count']
    # Add total row to ext_counts
    ext_counts.loc[len(ext_counts)] = ['TOTAL', total_files]
    
    # Count number of textracted files
    textracted_count = df['textracted'].fillna(False).sum() if 'textracted' in df.columns else 0
    
    # Count total token count - handle potential large numbers safely
    try:
        # First convert to float to handle potential non-numeric values
        df['token_count'] = pd.to_numeric(df['token_count'], errors='coerce').fillna(0)
        token_total = df['token_count'].sum()
        
        # Format large numbers as strings to avoid integer overflow
        token_total_str = f"{token_total:.1f}" if token_total > 1000000 else str(int(token_total))
        
        # Create token count dataframe
        token_count_df = pd.DataFrame({
            'metric': ['textracted_files', 'total_tokens'],
            'value': [str(int(textracted_count)), token_total_str]
        })
    except Exception as e:
        log_event(f"[ERROR] Error processing token count: {e}", verbose)
        token_count_df = pd.DataFrame({
            'metric': ['textracted_files', 'total_tokens'],
            'value': [str(int(textracted_count)), "Error calculating total"]
        })
    
    # Format output as plain text (for backward compatibility)
    summary_lines = []
    summary_lines.append("Files, textracted files, and token count per top-level folder:")
    summary_lines.append(folder_stats.to_string(index=False))
    summary_lines.append("\nFile count by extension:")
    summary_lines.append(ext_counts.to_string(index=False))
    summary_lines.append(f"\nNumber of textracted files: {int(total_textracted)}")
    summary_lines.append(f"Total token count: {int(total_tokens)}")
    
    summary_txt = "\n".join(summary_lines)
    
    # Save to CSV files
    folder_stats.to_csv(folder_breakdown_path, index=False)
    ext_counts.to_csv(extension_breakdown_path, index=False)
    log_event(f"[INFO] Saved analysis outputs to {folder_breakdown_path}, {extension_breakdown_path}", verbose)
    
    if output_mode == "print":
        log_event(summary_txt, verbose)
        print(summary_txt)
    elif output_mode == "return":
        log_event("[INFO] Returning analysis results as dict", verbose)
        return {
            "folder_stats": folder_stats,
            "ext_counts": ext_counts,
            "textracted_count": total_textracted,
            "token_total": total_tokens,
            "summary_txt": summary_txt,
            "csv_paths": {
                "folder_breakdown": str(folder_breakdown_path),
                "extension_breakdown": str(extension_breakdown_path)
            }
        }
    # output_mode == 'csv' does not print or return, just writes files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze catalog data for summary statistics.")
    parser.add_argument("--output_mode", default="csv", help="Output mode: print, csv (default), or return")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    analyze_catalog(output_mode=args.output_mode, verbose=args.verbose)
