#!/usr/bin/env python3
"""
identify.py | PDF Identification Entry Point
Purpose: Simple entry point for PDF identification workflow
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: Same as catalog.py
Abstract Spec: Provides a dedicated entry point for the PDF identification workflow
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import the necessary modules from the existing codebase
from agents.PDF_renamer import process_pdf_directory
from adapters.llm_provider import get_llm_provider
from core.file_utils import load_prompt
from ports.profile_loader import add_profile_arg, load_profile_config

# Load environment variables
load_dotenv()

def main():
    """
    Purpose: CLI entry point for PDF identification workflow.
    Inputs:
        --profile: Library profile to use (from folder_paths.json)
        --verbose: Enable verbose logging
    Outputs: None
    Role: Provides a simple entry point to the PDF identification workflow.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="PDF Identification Tool")
    add_profile_arg(parser)  # Add the --profile argument
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    try:
        # Load profile-specific config
        profile_config = load_profile_config(args=args)
        
        # Check if buffer_folder is defined in the profile
        if "buffer_folder" not in profile_config:
            raise KeyError(f"[ERROR] Required key 'buffer_folder' not found in selected profile")
        
        buffer_folder = profile_config["buffer_folder"]
        prompt = load_prompt("agents/PDF_renamer_prompt.txt")
        
        # Use the workflow-specific LLM provider for identification
        llm = get_llm_provider(workflow="identify")
        
        # Process the PDFs in the buffer folder
        process_pdf_directory(Path(buffer_folder), llm, prompt, n_pages=5, verbose=args.verbose)
        
    except Exception as e:
        print(str(e))
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
