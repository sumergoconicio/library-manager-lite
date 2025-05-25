"""
main.py | Entry Point
Purpose: Orchestrate config loading, catalog processing, and catalog analysis for Library Manager.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-24
Non-Std Deps: pandas, PyMuPDF (fitz)
Abstract Spec: Loads config, runs catalog and extraction workflow, or analyzes catalog per CLI flag.
Provides robust help system that can handle future flags.
"""

from pathlib import Path
import sys
from core.catalog_files import run_catalog_workflow
from core.catalog_analyzer import analyze_catalog

def display_help(parser):
    """
    Purpose: Display enhanced help message with all available flags.
    Inputs: parser (argparse.ArgumentParser)
    Outputs: None (prints to console)
    Role: Provides user-friendly help information about all available flags.
    """
    # Get all actions from parser
    actions = parser._actions
    
    print("\nLibrary Manager Lite - PDF Text Extraction and Cataloging System\n")
    print("USAGE:")
    print("  python main.py [FLAGS]\n")
    print("FLAGS:")
    
    # Filter out the default help action
    flag_actions = [action for action in actions if action.option_strings]
    
    # Calculate the maximum length for padding
    max_flag_length = max(len(action.option_strings[0]) for action in flag_actions) + 2
    
    # Print each flag with its help text, properly aligned
    for action in flag_actions:
        flag = action.option_strings[0]
        help_text = action.help
        print(f"  {flag:<{max_flag_length}} {help_text}")
    
    print("\nEXAMPLES:")
    print("  python main.py                      # Run incremental catalog update")
    print("  python main.py --catalog            # Regenerate catalog from scratch")
    print("  python main.py --analysis           # Analyze existing catalog")
    print("  python main.py --convert            # Extract text from PDFs and convert MD to TXT")
    print("  python main.py --verbose --tokenize # Run with verbose logging and token counting")
    print("  python main.py --convert --tokenize # Extract text and count tokens")
    print()

def main():
    """
    Purpose: CLI entry point for Library Manager.
    Inputs:
        --catalog: Regenerate catalog from scratch (force new)
        --analysis: Run catalog analysis and output summary to latest-breakdown.txt
        --verbose: Enable verbose logging to core/logs.txt
        --tokenize: Enable token-counting in catalog_files.py
        --convert: Convert MD files to TXT and extract text from PDFs
        --help: Display help message with all available flags
    Outputs: None
    Role: Loads config, runs incremental or full catalog workflow per CLI flags, passes flags to modules. 
    By default, only new files are appended to the catalog (incremental update). 
    Tokenization is only performed if --tokenize is set.
    Text extraction and conversion only occur if --convert is set.
    Provides enhanced help system that can handle future flags.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Library Manager Lite", add_help=False)
    parser.add_argument("--catalog", action="store_true", help="Regenerate catalog from scratch (force new)")
    parser.add_argument("--analysis", action="store_true", help="Run catalog analysis and output summary to latest-breakdown.txt")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging to core/logs.txt")
    parser.add_argument("--tokenize", action="store_true", help="Enable token-counting in catalog_files.py")
    parser.add_argument("--convert", action="store_true", help="Convert MD files to TXT and extract text from PDFs")
    parser.add_argument("--help", "-h", action="store_true", help="Display this help message and exit")
    
    args = parser.parse_args()
    
    # Check for help flag first
    if args.help:
        display_help(parser)
        sys.exit(0)
        
    config_path = Path("user_inputs/folder_paths.json")
    if args.catalog:
        run_catalog_workflow(config_path, verbose=args.verbose, tokenize=args.tokenize, force_new=True, convert=args.convert)
    elif args.analysis:
        print("[DEBUG] Starting catalog analysis...")
        analyze_catalog(output_mode="print")
        print("[DEBUG] Analysis complete. Output written to latest-breakdown.txt.")
    else:
        # Default: incremental update, append only new files
        run_catalog_workflow(config_path, verbose=args.verbose, tokenize=args.tokenize, force_new=False, convert=args.convert)

if __name__ == "__main__":
    main()
