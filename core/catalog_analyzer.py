"""
catalog_analyzer.py | Catalog Analysis Module
Purpose: Analyze catalog CSV for file/folder/extension/token statistics and output summary as CSV files.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-24
Non-Std Deps: pandas
Abstract Spec: Loads catalog CSV, computes summary statistics (files per folder with totals, extensions with totals, textracted files, token counts), outputs tables as separate CSV files (latest-folder-breakdown.csv, latest-extension-breakdown.csv, latest-token-count.csv).
"""

from core.log_utils import log_event

def analyze_catalog(output_mode="csv", verbose: bool = False):
    """
    Purpose: Analyze catalog CSV and output summary tables as separate CSV files.
    Inputs: output_mode (str: 'print', 'return', or 'csv'), verbose (bool)
    Outputs: None or dict of tables
    Role: Loads config, resolves catalog path, computes file/folder/ext/token stats with totals, counts textracted files, 
          writes separate CSV files for folder breakdown, extension breakdown, and token count.
    """
    import pandas as pd
    import json
    from pathlib import Path
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
    catalog_path = Path(root_folder) / catalog_folder / "latest-catalog.csv"
    
    # Define paths for the separate CSV files
    folder_breakdown_path = Path(root_folder) / catalog_folder / "latest-folder-breakdown.csv"
    extension_breakdown_path = Path(root_folder) / catalog_folder / "latest-extension-breakdown.csv"
    token_count_path = Path(root_folder) / catalog_folder / "latest-token-count.csv"
    
    if not catalog_path.exists():
        log_event(f"[ERROR] Catalog file not found: {catalog_path}", verbose)
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
    df = pd.read_csv(catalog_path)
    # Check required columns
    required_cols = ["relative_path", "extension"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        log_event(f"[ERROR] Missing required columns in catalog: {missing}. Available columns: {list(df.columns)}", verbose)
        raise KeyError(f"Missing required columns in catalog: {missing}. Available columns: {list(df.columns)}")
    # Count total files per top-level folder
    df['top_folder'] = df['relative_path'].apply(lambda x: x.split('/')[0] if '/' in x else x)
    files_per_folder = df.groupby('top_folder').size().reset_index(name='file_count')
    # Add total row to files_per_folder
    total_files = files_per_folder['file_count'].sum()
    files_per_folder.loc[len(files_per_folder)] = ['TOTAL', total_files]
    
    # Count unique extension types
    ext_counts = df['extension'].value_counts().reset_index()
    ext_counts.columns = ['extension', 'file_count']
    # Add total row to ext_counts
    ext_counts.loc[len(ext_counts)] = ['TOTAL', total_files]
    
    # Count number of textracted files
    textracted_count = df['textracted'].fillna(False).sum() if 'textracted' in df.columns else 0
    
    # Count total token count
    token_total = df['token_count'].fillna(0).sum()
    # Create token count dataframe
    token_count_df = pd.DataFrame({
        'metric': ['textracted_files', 'total_tokens'],
        'value': [int(textracted_count), int(token_total)]
    })
    
    # Format output as plain text (for backward compatibility)
    summary_lines = []
    summary_lines.append("Total files per top-level folder:")
    summary_lines.append(files_per_folder.to_string(index=False))
    summary_lines.append("\nFile count by extension:")
    summary_lines.append(ext_counts.to_string(index=False))
    summary_lines.append(f"\nNumber of textracted files: {int(textracted_count)}")
    summary_lines.append(f"Total token count: {int(token_total)}")
    summary_txt = "\n".join(summary_lines)
    
    # Save to CSV files
    files_per_folder.to_csv(folder_breakdown_path, index=False)
    ext_counts.to_csv(extension_breakdown_path, index=False)
    token_count_df.to_csv(token_count_path, index=False)
    log_event(f"[INFO] Saved analysis outputs to {folder_breakdown_path}, {extension_breakdown_path}, {token_count_path}", verbose)
    
    if output_mode == "print":
        log_event(summary_txt, verbose)
        print(summary_txt)
    elif output_mode == "return":
        log_event("[INFO] Returning analysis results as dict", verbose)
        return {
            "files_per_folder": files_per_folder,
            "ext_counts": ext_counts,
            "textracted_count": textracted_count,
            "token_total": token_total,
            "summary_txt": summary_txt,
            "csv_paths": {
                "folder_breakdown": str(folder_breakdown_path),
                "extension_breakdown": str(extension_breakdown_path),
                "token_count": str(token_count_path)
            }
        }
    # output_mode == 'csv' does not print or return, just writes files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze catalog CSV for summary statistics.")
    parser.add_argument("--output_mode", default="csv", help="Output mode: print, csv (default), or return")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    analyze_catalog(output_mode=args.output_mode, verbose=args.verbose)
    analyze_catalog(output_mode=args.output_mode)
