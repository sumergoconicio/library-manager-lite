"""
main.py | Entry Point
Purpose: Orchestrate config loading, catalog processing, and catalog analysis for Library Manager.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-02
Non-Std Deps: pandas, PyMuPDF (fitz)
Abstract Spec: Loads config, runs catalog and extraction workflow, or analyzes catalog per CLI flag.
Provides robust help system that can handle future flags.
"""

from pathlib import Path
import sys
from dotenv import load_dotenv
import argparse
import json
import litellm
from ports.profile_loader import load_profile_config, add_profile_arg

# Enable LiteLLM debug logging for troubleshooting provider/model issues
#try:
#    import litellm
#    litellm._turn_on_debug()
#except ImportError:
#    pass

from core.catalog_files import run_catalog_workflow
from core.catalog_analyzer import analyze_catalog
from core.file_utils import load_config, load_prompt

load_dotenv()

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
    print("  python catalog.py [FLAGS]\n")
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
    print("  python catalog.py                      # Run incremental catalog update with analysis")
    print("  python catalog.py --recatalog          # Force regenerate catalog from scratch with analysis")
    print("  python catalog.py --no-analysis        # Run incremental update without analysis")
    print("  python catalog.py --analysis           # Only analyze existing catalog (no updates)")
    print("  python catalog.py --convert            # Extract text from PDFs and convert MD to TXT")
    print("  python catalog.py --verbose --tokenize # Run with verbose logging and token counting")
    print("  python catalog.py --convert --tokenize # Extract text and count tokens")
    print("  python catalog.py --identify           # Rename PDFs in buffer folder using LLM")
    print("  python catalog.py --transcribe         # Download transcripts from YouTube videos")
    print("  python catalog.py --search             # Search for files by filename in the SQLite database")
    print("  python catalog.py --help               # Display this help message and exit")
    print()

def main():
    """
    Purpose: CLI entry point for Library Manager.
    Inputs:
        --recatalog: Force regenerate catalog from scratch (full refresh). Automatically includes text conversion and tokenization.
        --analysis: Run catalog analysis and output summary to latest-breakdown.txt
        --verbose: Enable verbose logging to core/logs.txt
        --tokenize: Enable token-counting in catalog_files.py
        --convert: Convert MD files to TXT and extract text from PDFs
        --identify: Run PDF renaming workflow on buffer_folder
        --transcribe: Download transcripts from YouTube videos
        --search: Search for files by filename in the SQLite database
        --help: Display this help message and exit
    Outputs: None
    Role: Loads config, runs incremental or full catalog workflow per CLI flags, passes flags to modules. 
    By default, only new files are appended to the catalog (incremental update) and analysis is run afterward.
    Tokenization is always enabled for catalog operations.
    Text extraction and conversion are always enabled for catalog operations.
    Provides enhanced help system that can handle future flags.
    """
    # Short-circuit recommend flag before parsing other flags to avoid unrecognized argument errors
    if "--recommend" in sys.argv:
        # Invoke the standalone recommendation script
        from subprocess import run
        script = Path(__file__).resolve().parent / "recommend.py"
        # Remove the --recommend flag before passing through
        args_to_pass = [arg for arg in sys.argv[1:] if arg != "--recommend"]
        run([sys.executable, str(script)] + args_to_pass)
        sys.exit(0)
    parser = argparse.ArgumentParser(description="Library Manager Lite", add_help=False)
    parser.add_argument("--recatalog", action="store_true", help="Force regenerate catalog from scratch (full refresh). Automatically includes text conversion and tokenization.")
    parser.add_argument("--analysis", action="store_true", default=None, help="Run catalog analysis and output summary to latest-breakdown.txt")
    parser.add_argument("--no-analysis", action="store_false", dest="analysis", help="Skip running catalog analysis (overrides default behavior)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging to core/logs.txt")
    parser.add_argument("--tokenize", action="store_true", help="Enable token-counting in catalog_files.py")
    parser.add_argument("--convert", action="store_true", help="Convert MD files to TXT and extract text from PDFs")
    parser.add_argument("--identify", action="store_true", help="Run PDF renaming workflow on buffer_folder")
    parser.add_argument("--transcribe", action="store_true", help="Download transcripts from YouTube videos")
    parser.add_argument("--search", action="store_true", help="Search for files by filename in the SQLite database")
    parser.add_argument("--backupdb", action="store_true", help="Create a backup of the SQLite database in the catalog folder")
    parser.add_argument("--help", "-h", action="store_true", help="Display this help message and exit")
    # Add profile selection argument
    add_profile_arg(parser)
    
    # Parse known args to handle new flags gracefully
    args, unknown = parser.parse_known_args()
    if unknown:
        print(f"[WARNING] Unknown arguments: {unknown}")
        
    # If help flag is set, display help and exit
    if args.help:
        display_help(parser)
        sys.exit(0)

    # Dispatch table for CLI actions
    def handle_recatalog():
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        # When --recatalog is used, convert and tokenize are implicitly True
        run_catalog_workflow(profile_config, verbose=args.verbose, tokenize=True, force_new=True, convert=True, backup_db=args.backupdb)
        # Run analysis by default after recataloging
        handle_analysis()

    def handle_analysis(force_run=False):
        # Skip if analysis flag is explicitly set to False, unless force_run is True
        if not args.analysis and args.analysis is not None and not force_run:
            return
        
        # Use concise output by default, detailed output if explicitly requested with --analysis
        use_concise = not (args.analysis and not force_run)
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        analyze_catalog(output_mode="print", verbose=args.verbose, concise=use_concise, profile_config=profile_config)

    def handle_identify():
        from agents.PDF_renamer import process_pdf_directory
        from adapters.llm_provider import get_llm_provider
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        if "buffer_folder" not in profile_config:
            raise KeyError(f"[ERROR] Required key 'buffer_folder' not found in selected profile")
        buffer_folder = profile_config["buffer_folder"]
        prompt = load_prompt("agents/PDF_renamer_prompt.txt")
        # Use the workflow-specific LLM provider for identification
        llm = get_llm_provider(workflow="identify")
        process_pdf_directory(Path(buffer_folder), llm, prompt, n_pages=5, verbose=args.verbose)

    def handle_transcribe():
        from adapters.yt_transcriber import process_transcript_request
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        if "yt_transcripts_folder" not in profile_config:
            raise KeyError(f"[ERROR] Required key 'yt_transcripts_folder' not found in selected profile")
        process_transcript_request(profile_config, verbose=args.verbose)
        # Run incremental catalog update after transcription with tokenize=True
        print("[INFO] Running incremental catalog update to include new transcript files...")
        run_catalog_workflow(profile_config, verbose=args.verbose, tokenize=True, force_new=False, convert=False, backup_db=args.backupdb)
        print("[INFO] Catalog update complete with token counting enabled.")

    def handle_search():
        from adapters.search_and_retrieve import interactive_search
        # Delegate entire workflow to adapter to keep main.py lightweight
        results = interactive_search(args)
        if args.verbose:
            print("RETURNED TYPE:", type(results))
            print("RETURNED VALUE:", results)
            
    def handle_incremental():
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        # Always enable convert and tokenize for incremental updates
        run_catalog_workflow(profile_config, verbose=args.verbose, tokenize=True, force_new=False, convert=True, backup_db=args.backupdb)
        # Run analysis by default after incremental update
        handle_analysis()

    # Help flag already handled above
    # Dispatch logic
    if args.identify:
        try:
            handle_identify()
        except Exception as e:
            print(str(e))
            sys.exit(1)
        sys.exit(0)
    elif args.transcribe:
        try:
            handle_transcribe()
        except Exception as e:
            print(str(e))
            sys.exit(1)
        sys.exit(0)
    elif args.search:
        try:
            handle_search()
        except Exception as e:
            print(str(e))
            sys.exit(1)
        sys.exit(0)
    elif args.recatalog:
        handle_recatalog()
    elif args.analysis:
        # Only run analysis if explicitly requested
        handle_analysis(force_run=True)
    else:
        handle_incremental()

if __name__ == "__main__":
    main()
