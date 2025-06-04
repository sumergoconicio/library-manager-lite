"""
Title: YouTube Transcript Archive Manager
Description: Manages a CSV archive of downloaded YouTube transcripts to prevent duplicates.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-06-03
Dependencies: pathlib, csv, os
Design Rationale: Provides a clean interface for tracking downloaded transcripts with CSV persistence.
"""

import os
import csv
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import re

def is_transcript_in_archive(video_url: str, filename: str, archive_path: Path, verbose: bool = False) -> bool:
    """
    Purpose: Check if a transcript is already in the archive
    Inputs:
        video_url (str): URL of the YouTube video
        filename (str): Filename of the transcript (without path)
        archive_path (Path): Path to the archive CSV file
        verbose (bool): Whether to enable verbose logging
    Outputs:
        bool: True if transcript is in archive, False otherwise
    Role: Core function for transcript archive checking
    """
    from core.log_utils import log_event
    
    if not archive_path.exists():
        if verbose:
            log_event(f"Archive file {archive_path} does not exist yet", verbose)
        return False
        
    try:
        with open(archive_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header if exists
            try:
                next(reader)
            except StopIteration:
                # Empty file, no header
                return False
                
            # Extract video ID from URL for more reliable comparison
            video_id = extract_video_id(video_url)
            
            for row in reader:
                if len(row) >= 2:
                    # Check if either filename or video ID matches
                    stored_filename = row[0]
                    stored_url = row[1]
                    stored_video_id = extract_video_id(stored_url)
                    
                    if stored_filename == filename or (video_id and stored_video_id == video_id):
                        if verbose:
                            log_event(f"Transcript for {video_url} already in archive", verbose)
                        return True
                        
        if verbose:
            log_event(f"Transcript for {video_url} not found in archive", verbose)
        return False
        
    except Exception as e:
        # Log error but continue (assume not in archive)
        if verbose:
            log_event(f"Error checking transcript archive: {str(e)}", verbose)
        return False

def add_transcript_to_archive(video_url: str, filename: str, archive_path: Path, verbose: bool = False) -> bool:
    """
    Purpose: Add a transcript to the archive
    Inputs:
        video_url (str): URL of the YouTube video
        filename (str): Filename of the transcript (without path)
        archive_path (Path): Path to the archive CSV file
        verbose (bool): Whether to enable verbose logging
    Outputs:
        bool: True if successful, False otherwise
    Role: Core function for transcript archive management
    """
    from core.log_utils import log_event
    
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(archive_path.parent, exist_ok=True)
        
        # Check if file exists to determine if we need to write headers
        file_exists = archive_path.exists() and archive_path.stat().st_size > 0
        
        with open(archive_path, 'a+', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header if file is new
            if not file_exists:
                writer.writerow(['Filename', 'URL', 'Date Added'])
                
            # Get current date in ISO format
            from datetime import datetime
            date_added = datetime.now().strftime('%Y-%m-%d')
            
            # Write transcript info
            writer.writerow([filename, video_url, date_added])
            
        if verbose:
            log_event(f"Added transcript {filename} for {video_url} to archive", verbose)
        return True
        
    except Exception as e:
        # Log error
        error_msg = f"Error adding to transcript archive: {str(e)}"
        print(error_msg)
        if verbose:
            log_event(error_msg, verbose)
        return False

def extract_video_id(video_url: str) -> Optional[str]:
    """
    Purpose: Extract YouTube video ID from URL
    Inputs:
        video_url (str): URL of the YouTube video
    Outputs:
        Optional[str]: Video ID if found, None otherwise
    Role: Helper function for transcript archive management
    """
    # Match common YouTube URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:&|$|\?)',  # Standard YouTube URLs
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',      # Short youtu.be URLs
        r'(?:embed\/)([0-9A-Za-z_-]{11})',          # Embed URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
            
    return None

def get_archive_path(catalog_folder: Path, verbose: bool = False) -> Path:
    """
    Purpose: Get the path to the transcript archive file
    Inputs:
        catalog_folder (Path): Path to the catalog folder
        verbose (bool): Whether to enable verbose logging
    Outputs:
        Path: Path to the transcript archive file
    Role: Helper function for transcript archive management
    """
    from core.log_utils import log_event
    
    archive_path = catalog_folder / "latest-transcript-archive.csv"
    
    if verbose:
        log_event(f"Using transcript archive at: {archive_path}", verbose)
        
    return archive_path

def process_transcript_archive(video_url: str, filename: str, catalog_folder: Path, verbose: bool = False) -> bool:
    """
    Purpose: Process a transcript for archiving
    Inputs:
        video_url (str): URL of the YouTube video
        filename (str): Filename of the transcript (without path)
        catalog_folder (Path): Path to the catalog folder
        verbose (bool): Whether to enable verbose logging
    Outputs:
        bool: True if transcript should be downloaded, False if it's already in archive
    Role: Main entry point for transcript archive processing
    """
    from core.log_utils import log_event
    
    # Get archive path
    archive_path = get_archive_path(catalog_folder, verbose)
    
    # Check if transcript is already in archive
    if is_transcript_in_archive(video_url, filename, archive_path, verbose):
        if verbose:
            log_event(f"Transcript for {video_url} already in archive, skipping", verbose)
        return False
        
    # Add transcript to archive
    success = add_transcript_to_archive(video_url, filename, archive_path, verbose)
    
    if success and verbose:
        log_event(f"Successfully added transcript for {video_url} to archive", verbose)
        
    return success
