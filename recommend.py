#!/usr/bin/env python
"""
recommend.py | Book Recommendation Entry Point
Purpose: Standalone entry point for book recommendation functionality
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: Same as agents/book_recommender.py
Abstract Spec: Provides direct access to book recommendation functionality without going through main.py
"""

import sys
import argparse
from pathlib import Path

# Ensure project root is in sys.path for absolute imports
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import necessary modules
try:
    from agents.book_recommender import main as recommend_main
    from ports.profile_loader import add_profile_arg
except ModuleNotFoundError as e:
    print(f"\n[ImportError] Could not import required modules: {e}")
    sys.exit(1)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Book recommendation system based on search results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("query", nargs="?", type=str, help="Research query (optional)")
    # Add profile selection argument
    add_profile_arg(parser)
    
    args = parser.parse_args()
    
    # Call the book recommender's main function with the parsed arguments
    recommend_main(args, args.query if hasattr(args, 'query') else None)

if __name__ == "__main__":
    main()
