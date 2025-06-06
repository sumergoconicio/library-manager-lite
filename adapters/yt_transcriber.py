"""
Title: YouTube Transcript Downloader
Description: Downloads transcripts from YouTube videos or playlists using yt-dlp. Supports YouTube cookies via user_inputs/yt_cookie.txt for restricted/private videos.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-06-06
Dependencies: yt-dlp, pathlib, os
Design Rationale: Provides a clean interface for downloading YouTube transcripts with configurable output paths and cookie authentication.
"""

import os
from pathlib import Path
from typing import Optional, List
import yt_dlp
import glob
from ports.transcript_archive import process_transcript_archive, extract_video_id

def download_transcript(
    video_url: str, 
    output_folder: Path,
    catalog_folder: Path,
    subfolder: Optional[str] = None,
    verbose: bool = False
) -> bool:
    """
    Purpose: Download transcript for a YouTube video or playlist using yt-dlp.
    Inputs: 
        video_url (str): URL of the YouTube video or playlist
        output_folder (Path): Base folder to save transcripts
        catalog_folder (Path): Folder for storing download archive
        subfolder (Optional[str]): Optional subfolder within output_folder
        verbose (bool): Whether to enable verbose logging
    Outputs: 
        bool: True if successful, False otherwise
    Role: Core function for YouTube transcript downloading.
    """
    from core.log_utils import log_event
    
    try:
        # Create full output path with optional subfolder
        full_output_path = output_folder
        if subfolder:
            full_output_path = output_folder / subfolder
            os.makedirs(full_output_path, exist_ok=True)
        else:
            os.makedirs(output_folder, exist_ok=True)
            
        # Format the output template
        output_template = str(full_output_path / "%(upload_date)s %(title)s.%(ext)s")
        
        # Create download archive path for yt-dlp internal use
        download_archive = str(catalog_folder / "latest-transcript-archive.txt")
        
        # Print status message regardless of verbose mode
        print(f"Using download archive: {download_archive}")
        
        # Ensure catalog folder exists
        os.makedirs(catalog_folder, exist_ok=True)
        
        # Robust cookies logic: try with cookies if present & non-empty, else fallback to no cookies
        cookies_path = Path('user_inputs/yt_cookie.txt')
        use_cookies = cookies_path.exists() and cookies_path.stat().st_size > 0

        def get_ydl_opts(with_cookies, prefer_auto=True):
            opts = {
                'skip_download': True,
                'writeautomaticsub': prefer_auto,  # Only True if we want auto-generated captions
                'writesubtitles': not prefer_auto, # Only True if we want manual subtitles
                'subtitleslangs': ['en'],
                'subtitlesformat': 'vtt',
                'ignoreerrors': True,
                'outtmpl': output_template,
                'quiet': not verbose,
                'no_warnings': not verbose,
                'download_archive': download_archive
            }
            if with_cookies:
                opts['cookiefile'] = str(cookies_path)
            return opts

        # Step 1: Probe info to decide which subtitle type to download
        def probe_subtype_opts(with_cookies):
            with yt_dlp.YoutubeDL(get_ydl_opts(with_cookies, prefer_auto=True)) as ydl:
                info = ydl.extract_info(video_url, download=False)
                autosubs = info.get('automatic_captions', {})
                if verbose:
                    log_event(f"Probing: automatic_captions keys: {list(autosubs.keys())}", verbose)
                # Prefer auto-captions if available
                prefer_auto = 'en' in autosubs
                return prefer_auto


        tried_cookies = False
        if use_cookies:
            tried_cookies = True
            if verbose:
                log_event(f"Trying to use cookies file: {cookies_path}", verbose)
            try:
                # Probe for auto-captions
                prefer_auto = probe_subtype_opts(with_cookies=True)
                if verbose:
                    log_event(f"Cookie probe: prefer_auto={prefer_auto}", verbose)
                with yt_dlp.YoutubeDL(get_ydl_opts(with_cookies=True, prefer_auto=prefer_auto)) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    if verbose:
                        log_event(f"yt-dlp info.keys(): {list(info.keys())}", verbose)
                        subs = info.get('subtitles', {})
                        autosubs = info.get('automatic_captions', {})
                        log_event(f"Available subtitles: {list(subs.keys())}", verbose)
                        log_event(f"Available automatic captions: {list(autosubs.keys())}", verbose)
                        all_files = list(Path(output_folder).glob('*'))
                        log_event(f"All files after yt-dlp run: {[str(f) for f in all_files]}", verbose)
                        transcript_files = list(Path(output_folder).glob('*.vtt'))
                        log_event(f"VTT files after yt-dlp run: {[str(f) for f in transcript_files]}", verbose)
                    # Handle playlists
                    if info and 'entries' in info:
                        for entry in info['entries']:
                            if entry:
                                entry_id = entry.get('id')
                                entry_url = f"https://www.youtube.com/watch?v={entry_id}"
                                entry_title = entry.get('title', 'Unknown Title')
                                entry_date = entry.get('upload_date', 'Unknown Date')
                                expected_filename = f"{entry_date} {entry_title}.txt"
                                if process_transcript_archive(entry_url, expected_filename, catalog_folder, verbose):
                                    pass  # Place any per-video logic here if needed
                    return True
            except Exception as e:
                if verbose:
                    log_event(f"Failed to use cookies file ({cookies_path}): {str(e)}. Retrying without cookies.", verbose)
                print(f"Warning: Could not use cookies file ({cookies_path}): {str(e)}. Retrying without cookies...")

        if not tried_cookies or (tried_cookies and verbose):
            if verbose:
                log_event("Proceeding to download without cookies.", verbose)
        try:
            # Fallback: no cookies
            prefer_auto = probe_subtype_opts(with_cookies=False)
            if verbose:
                log_event(f"No-cookie probe: prefer_auto={prefer_auto}", verbose)
            with yt_dlp.YoutubeDL(get_ydl_opts(with_cookies=False, prefer_auto=prefer_auto)) as ydl:
                info = ydl.extract_info(video_url, download=True)
                # Verbose: log info dict and all files in output folder
                if verbose:
                    from core.log_utils import log_event
                    log_event(f"yt-dlp info.keys(): {list(info.keys())}", verbose)
                    subs = info.get('subtitles', {})
                    autosubs = info.get('automatic_captions', {})
                    log_event(f"Available subtitles: {list(subs.keys())}", verbose)
                    log_event(f"Available automatic captions: {list(autosubs.keys())}", verbose)
                    all_files = list(Path(output_folder).glob('*'))
                    log_event(f"All files after yt-dlp run: {[str(f) for f in all_files]}", verbose)
                    transcript_files = list(Path(output_folder).glob('*.vtt'))
                    log_event(f"VTT files after yt-dlp run: {[str(f) for f in transcript_files]}", verbose)
                # Handle playlists
                if info and 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            entry_id = entry.get('id')
                            entry_url = f"https://www.youtube.com/watch?v={entry_id}"
                            entry_title = entry.get('title', 'Unknown Title')
                            entry_date = entry.get('upload_date', 'Unknown Date')
                            expected_filename = f"{entry_date} {entry_title}.txt"
                            if process_transcript_archive(entry_url, expected_filename, catalog_folder, verbose):
                                pass  # Place any per-video logic here if needed
                return True
        except Exception as e:
            if verbose:
                log_event(f"Transcript download failed without cookies: {str(e)}", verbose)
            print(f"Transcript download failed: {str(e)}")
            return False

        
        if verbose:
            log_event(f"Running transcript download for: {video_url}", verbose)
            log_event(f"Output path: {output_template}", verbose)
            log_event(f"Download archive: {download_archive}", verbose)
            
        # Use yt-dlp as a library
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get video IDs
            info = ydl.extract_info(video_url, download=False)
            
            # Handle playlists
            if info and 'entries' in info:
                for entry in info['entries']:
                    if entry:
                        entry_id = entry.get('id')
                        entry_url = f"https://www.youtube.com/watch?v={entry_id}"
                        
                        # Generate expected filename
                        entry_title = entry.get('title', 'Unknown Title')
                        entry_date = entry.get('upload_date', 'Unknown Date')
                        expected_filename = f"{entry_date} {entry_title}.txt"
                        
                        # Check if transcript is already in archive
                        if process_transcript_archive(entry_url, expected_filename, catalog_folder, verbose):
                            # Download this specific video
                            ydl.download([entry_url])
                        else:
                            print(f"Skipping {entry_title} - already in transcript archive")
            # Handle single videos
            else:
                # Generate expected filename based on info if available
                expected_filename = "Unknown.txt"
                if info:
                    video_title = info.get('title', 'Unknown Title')
                    video_date = info.get('upload_date', 'Unknown Date')
                    expected_filename = f"{video_date} {video_title}.txt"
                
                # Check if transcript is already in archive
                if process_transcript_archive(video_url, expected_filename, catalog_folder, verbose):
                    # Download the video transcript
                    ydl.download([video_url])
                else:
                    print(f"Skipping {expected_filename} - already in transcript archive")
            
        if verbose:
            log_event(f"Successfully downloaded transcript to {full_output_path}", verbose)
            
        return True
        
    except Exception as e:
        # Always print critical errors regardless of verbose mode
        error_msg = f"Exception in download_transcript: {str(e)}"
        print(error_msg)
        if verbose:
            log_event(error_msg, verbose)
        return False

def convert_vtt_files(folder_path: Path, verbose: bool = False) -> List[str]:
    """
    Purpose: Convert all VTT files in a folder to TXT using convertVTTtoTXT.py
    Inputs:
        folder_path (Path): Path to folder containing VTT files
        verbose (bool): Whether to enable verbose logging
    Outputs:
        List[str]: List of created TXT file paths
    Role: Helper function to process VTT files after download
    """
    from core.log_utils import log_event
    from ports.convertVTTtoTXT import extract_vtt_to_txt
    
    converted_files = []
    
    if verbose:
        log_event(f"Searching for VTT files in {folder_path}", verbose)
    
    # Find all VTT files in the folder
    vtt_files = list(folder_path.glob("**/*.vtt"))
    
    if not vtt_files:
        if verbose:
            log_event("No VTT files found to convert", verbose)
        return converted_files
    
    if verbose:
        log_event(f"Found {len(vtt_files)} VTT files to convert", verbose)
    
    # Convert each VTT file to TXT
    for vtt_file in vtt_files:
        try:
            if verbose:
                log_event(f"Converting {vtt_file} to TXT", verbose)
            
            # The extract_vtt_to_txt function already handles deletion of the original VTT file
            txt_path = extract_vtt_to_txt(str(vtt_file), verbose)
            converted_files.append(txt_path)
            
            if verbose:
                log_event(f"Successfully converted {vtt_file} to {txt_path}", verbose)
                
        except Exception as e:
            if verbose:
                log_event(f"Error converting {vtt_file}: {str(e)}", verbose)
    
    return converted_files
        
def process_transcript_request(config: dict, verbose: bool = False) -> None:
    """
    Purpose: Process a transcript download request with user input.
    Inputs: 
        config (dict): Configuration dictionary with yt_transcripts_folder
        verbose (bool): Whether to enable verbose logging
    Outputs: None
    Role: Main entry point for transcript downloading workflow.
    """
    from core.log_utils import log_event
    
    # Get transcript folder from config
    if "yt_transcripts_folder" not in config:
        raise KeyError("yt_transcripts_folder not found in configuration")
        
    if "catalog_folder" not in config:
        raise KeyError("catalog_folder not found in configuration")
        
    transcript_folder = Path(config["yt_transcripts_folder"])
    catalog_folder = Path(config["catalog_folder"])
    
    # Create catalog folder if it doesn't exist
    os.makedirs(catalog_folder, exist_ok=True)
    
    # Get video URL from user
    video_url = input("Enter YouTube video or playlist URL: ")
    if not video_url:
        print("No URL provided. Exiting.")
        return
        
    # Ask for optional subfolder
    subfolder = input("Enter optional subfolder name (press Enter to skip): ").strip()
    subfolder = subfolder if subfolder else None
    
    # Download transcript
    if verbose:
        log_event(f"Starting transcript download for {video_url}", verbose)
        
    success = download_transcript(video_url, transcript_folder, catalog_folder, subfolder, verbose)
    
    if success:
        print(f"Transcript(s) downloaded successfully to {transcript_folder}/{subfolder if subfolder else ''}")
        if verbose:
            log_event(f"Transcript download completed successfully", verbose)
            
        # Determine the output folder path
        output_folder = transcript_folder
        if subfolder:
            output_folder = transcript_folder / subfolder
            
        # Convert VTT files to TXT and delete originals
        if verbose:
            log_event("Starting VTT to TXT conversion", verbose)
            
        converted_files = convert_vtt_files(output_folder, verbose)
        
        if converted_files:
            print(f"Converted {len(converted_files)} VTT files to TXT format")
            if verbose:
                log_event(f"VTT to TXT conversion completed: {len(converted_files)} files processed", verbose)
        else:
            print("No VTT files found to convert")
            if verbose:
                log_event("No VTT files were converted", verbose)
    else:
        print("Failed to download transcript(s). Check the URL and try again.")
        if verbose:
            log_event("Transcript download failed", verbose)
