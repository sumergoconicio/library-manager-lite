"""
main.py | Entry Point
Purpose: Orchestrate config loading, catalog processing, and catalog analysis for Library Manager.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-23
Non-Std Deps: pandas, PyMuPDF (fitz)
Abstract Spec: Loads config, runs catalog and extraction workflow, or analyzes catalog per CLI flag.
"""

from pathlib import Path
from core.catalog_files import run_catalog_workflow
from core.catalog_analyzer import analyze_catalog

def main():
    """
    Purpose: CLI entry point for Library Manager.
    Inputs:
        --catalog: Regenerate catalog from scratch (force new)
        --analysis: Run catalog analysis and output summary to latest-breakdown.txt
        --verbose: Enable verbose logging to core/logs.txt
        --tokenize: Enable token-counting in catalog_files.py
    Outputs: None
    Role: Loads config, runs incremental or full catalog workflow per CLI flags, passes flags to modules. By default, only new files are appended to the catalog (incremental update). Tokenization is only performed if --tokenize is set.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Library Manager Lite")
    parser.add_argument("--catalog", action="store_true", help="Regenerate catalog from scratch (force new)")
    parser.add_argument("--analysis", action="store_true", help="Run catalog analysis and output summary to latest-breakdown.txt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging to core/logs.txt")
    parser.add_argument("--tokenize", action="store_true", help="Enable token-counting in catalog_files.py")
    args = parser.parse_args()
    config_path = Path("user_inputs/folder_paths.json")
    if args.catalog:
        run_catalog_workflow(config_path, verbose=args.verbose, tokenize=args.tokenize, force_new=True)
    elif args.analysis:
        print("[DEBUG] Starting catalog analysis...")
        analyze_catalog(output_mode="print")
        print("[DEBUG] Analysis complete. Output written to latest-breakdown.txt.")
    else:
        # Default: incremental update, append only new files
        run_catalog_workflow(config_path, verbose=args.verbose, tokenize=args.tokenize, force_new=False)

if __name__ == "__main__":
    main()
