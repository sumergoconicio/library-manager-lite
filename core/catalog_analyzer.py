"""
catalog_analyzer.py | Catalog Analysis Module
Purpose: Analyze catalog CSV for file/folder/extension/token statistics and output summary as latest-breakdown.txt (plain text).
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-23
Non-Std Deps: pandas
Abstract Spec: Loads catalog CSV, computes summary statistics, outputs tables as plain text to latest-breakdown.txt.
"""

def analyze_catalog(output_mode="print"):
    """
    Purpose: Analyze catalog CSV and output summary tables as plain text to latest-breakdown.txt.
    Inputs: output_mode (str: 'print', 'return', or 'txt')
    Outputs: None or dict of tables
    Role: Loads config, resolves catalog path, computes file/folder/ext/token stats, writes summary to latest-breakdown.txt.
    """
    import pandas as pd
    import json
    from pathlib import Path
    config_path = Path("user_inputs/folder_paths.json")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as f:
        config = json.load(f)
    root_folder = config.get("root_folder_path")
    catalog_folder = config.get("catalog_folder", "_catalog")
    if not root_folder:
        raise ValueError("root_folder_path must be set in user_inputs/folder_paths.json")
    catalog_path = Path(root_folder) / catalog_folder / "latest-catalog.csv"
    breakdown_path = Path(root_folder) / catalog_folder / "latest-breakdown.txt"
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
    df = pd.read_csv(catalog_path)
    # Check required columns
    required_cols = ["relative_path", "extension", "token_count"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in catalog: {missing}. Available columns: {list(df.columns)}")
    # Count total files per top-level folder
    df['top_folder'] = df['relative_path'].apply(lambda x: x.split('/')[0] if '/' in x else x)
    files_per_folder = df.groupby('top_folder').size().reset_index(name='file_count')
    # Count unique extension types
    ext_counts = df['extension'].value_counts().reset_index()
    ext_counts.columns = ['extension', 'file_count']
    # Count total token count
    token_total = df['token_count'].fillna(0).sum()
    # Format output as plain text
    summary_lines = []
    summary_lines.append("Total files per top-level folder:")
    summary_lines.append(files_per_folder.to_string(index=False))
    summary_lines.append("\nFile count by extension:")
    summary_lines.append(ext_counts.to_string(index=False))
    summary_lines.append(f"\nTotal token count: {int(token_total)}")
    summary_txt = "\n".join(summary_lines)
    # Always write to latest-breakdown.txt
    with open(breakdown_path, "w", encoding="utf-8") as f:
        f.write(summary_txt)
    if output_mode == "print":
        print(summary_txt)
    elif output_mode == "return":
        return {
            "files_per_folder": files_per_folder,
            "ext_counts": ext_counts,
            "token_total": token_total,
            "summary_txt": summary_txt
        }
    # output_mode == 'txt' does not print or return, just writes file

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze catalog CSV for summary statistics.")
    parser.add_argument("--output_mode", default="print", help="Output mode: print (default) or return")
    args = parser.parse_args()
    analyze_catalog(output_mode=args.output_mode)
