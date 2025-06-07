#!/usr/bin/env python3
"""
transcribe.py | YouTube Transcript Entry Point
Purpose: Simple entry point for YouTube transcript download workflow
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: Same as catalog.py
Abstract Spec: Provides a dedicated entry point for the YouTube transcript download workflow
"""

import sys
import argparse
from dotenv import load_dotenv

# Import the necessary modules from the existing codebase
from adapters.yt_transcriber import process_transcript_request
from core.catalog_files import run_catalog_workflow
from ports.profile_loader import add_profile_arg, load_profile_config

# Load environment variables
load_dotenv()

def main():
    """
    Purpose: CLI entry point for YouTube transcript download workflow.
    Inputs:
        --profile: Library profile to use (from folder_paths.json)
        --verbose: Enable verbose logging
        --backupdb: Backup the SQLite database before making changes
    Outputs: None
    Role: Provides a simple entry point to the YouTube transcript download workflow.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="YouTube Transcript Download Tool")
    add_profile_arg(parser)  # Add the --profile argument
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--backupdb", action="store_true", help="Backup the SQLite database before making changes")
    args = parser.parse_args()

    try:
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        
        # Check if yt_transcripts_folder is defined in the profile
        if "yt_transcripts_folder" not in profile_config:
            raise KeyError(f"[ERROR] Required key 'yt_transcripts_folder' not found in selected profile")
        
        # Process the transcript request
        process_transcript_request(profile_config, verbose=args.verbose)
        
        # Run incremental catalog update after transcription with tokenize=True
        print("[INFO] Running incremental catalog update to include new transcript files...")
        run_catalog_workflow(profile_config, verbose=args.verbose, tokenize=True, 
                            force_new=False, convert=False, backup_db=args.backupdb)
        print("[INFO] Catalog update complete with token counting enabled.")
        
    except Exception as e:
        print(str(e))
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
