"""
core/catalog_files.py | Catalog Management Module
Purpose: Scan root folder for PDFs, update catalog CSV, trigger extraction as needed. (NEW: Count tokens in TXT files using tiktoken)
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-05-23
Non-Std Deps: pandas, tiktoken
Abstract Spec: Loads config, manages catalog, triggers extraction for new PDFs, and counts tokens in TXT files.
"""

import os
from pathlib import Path
import pandas as pd
import json
from core.extract_text import extract_and_save
from core.convertMDtoTXT import convert_md_to_txt
from core.file_utils import get_file_extension
from core.token_counter import count_tokens


def load_config(config_path: Path) -> dict:
    """
    Purpose: Load and validate user config from JSON.
    Inputs: config_path (Path)
    Outputs: config (dict)
    Role: Centralizes config loading and validation.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    root = Path(config['root_folder_path'])
    catalog_folder = config.get('catalog_folder', '_catalog')
    extract_path = config.get('extract_path', 'textracted')
    excluded_files = set(config.get('excluded_files', []))
    return {
        'root': root,
        'catalog_folder': catalog_folder,
        'extract_path': extract_path,
        'excluded_files': excluded_files
    }

def is_excluded(abs_file_path: Path, excluded: set, root: Path) -> bool:
    """
    Returns True if the file or any parent folder matches an entry in excluded (folders end with /).
    """
    rel = abs_file_path.relative_to(root)
    # Check file itself
    if rel.name in excluded:
        return True
    # Check parent folders
    parts = rel.parts
    for i in range(len(parts)):
        folder = parts[i]
        folder_key = folder + '/'  # convention: folders end with /
        if folder_key in excluded:
            return True
    return False


def load_or_init_catalog(root: Path, catalog_folder: str) -> pd.DataFrame:
    """
    Purpose: Load existing catalog or initialize new DataFrame.
    Inputs: root (Path), catalog_folder (str)
    Outputs: catalog (pd.DataFrame)
    Role: Ensures catalog is always available for update.
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / 'latest-catalog.csv'
    if catalog_path.exists():
        return pd.read_csv(catalog_path)
    cols = ['relative_path', 'filename', 'extension', 'textracted', 'token_count']
    return pd.DataFrame(columns=cols)

def get_first_level_subdir(root: Path, file_path: Path) -> Path:
    """
    Purpose: Given a file path under root, return the first-level subdirectory (or root if directly under root).
    Inputs: root (Path), file_path (Path)
    Outputs: Path to first-level subdirectory or root
    """
    rel = file_path.relative_to(root)
    parts = rel.parts
    if len(parts) == 1:
        # File is directly under root
        return root
    else:
        return root / parts[0]

EXCLUDED_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

def scan_and_update_catalog(
    root: Path, extract_folder: str, catalog: pd.DataFrame, excluded_files: set = None, verbose: bool = False, tokenize: bool = False, convert: bool = False
) -> pd.DataFrame:
    """
    core/catalog_files.py | Unified Catalog & Extraction Routine
    Purpose: Scan root recursively, catalog all files, extract text from PDFs (to textracted), convert MD to TXT, and update extraction/tokenization status.
    Author: ChAI-Engine (chaiji)
    Last-Updated: 2025-05-25
    Non-Std Deps: pandas, tiktoken, PyMuPDF (fitz)
    Abstract Spec: Only this implementation is active; legacy/duplicate code removed for audit clarity. See dev/project-intent.md.
    
    Purpose: Recursively scan root, catalog all files except system files and .txt files in textracted folders. For PDFs, if convert is True, extract text to the correct textracted folder. For MD files, if convert is True, convert to TXT in place. Update textracted/token_count status for catalog. Robust logging at start/end and for all key actions.
    Inputs:
        root (Path): Root directory to scan.
        extract_folder (str): Name of the extraction folder (e.g., 'textracted').
        catalog (pd.DataFrame): Existing catalog DataFrame.
        excluded_files (set): Files/folders to exclude.
        verbose (bool): Enable verbose logging.
        tokenize (bool): If True, count tokens in TXT files.
        convert (bool): If True, extract PDFs and convert MDs.
    Outputs:
        pd.DataFrame: Updated catalog DataFrame.
    Role: Single source of truth for cataloging, extraction, and conversion. Idempotent and compliant with project rules.
    """
    from core.log_utils import log_event
    log_event("[START] scan_and_update_catalog", verbose)
    if excluded_files is None:
        excluded_files = set()
    records = []
    for dirpath, dirs, files in os.walk(root):
        # Skip textracted folders entirely for cataloging
        if os.path.basename(dirpath) == extract_folder:
            continue
        if extract_folder in dirs:
            dirs.remove(extract_folder)
        for f in files:
            abs_file_path = Path(dirpath) / f
            if f in EXCLUDED_FILES:
                log_event(f"File skipped (excluded): {abs_file_path}", verbose)
                continue
            if excluded_files and is_excluded(abs_file_path, excluded_files, root):
                log_event(f"File skipped (excluded by config): {abs_file_path}", verbose)
                continue
            name, ext = os.path.splitext(f)
            rel_dir = os.path.relpath(dirpath, root)
            extension = get_file_extension(f)
            # Do not catalog .txt files in any textracted folder
            if extension.lower() == 'txt' and extract_folder in Path(dirpath).parts:
                log_event(f"File skipped (.txt in textracted): {abs_file_path}", verbose)
                continue
            record = {
                'relative_path': rel_dir,
                'filename': name,
                'extension': extension
            }
            if extension.lower() == 'pdf':
                # Compute correct textracted folder
                first_level = get_first_level_subdir(root, abs_file_path)
                txt_dir = first_level / extract_folder
                txt_path = txt_dir / (name + '.txt')
                already_in_catalog = (
                    (catalog['relative_path'] == rel_dir)
                    & (catalog['filename'] == name)
                    & (catalog['extension'] == ext.lstrip('.'))
                )
                skip_due_to_catalog = False
                if already_in_catalog.any():
                    # Already catalogued, check if extracted
                    textracted = catalog.loc[already_in_catalog, 'textracted'].iloc[0]
                    # Only skip if both catalog says extracted AND the .txt file actually exists
                    if (textracted == True or textracted == 'True') and txt_path.exists():
                        skip_due_to_catalog = True
                if skip_due_to_catalog:
                    log_event(f"File skipped (already extracted): {abs_file_path}", verbose)
                    record['textracted'] = True
                    if tokenize:
                        try:
                            token_count = count_tokens(str(txt_path))
                            record['token_count'] = token_count
                            log_event(f"Token count for {txt_path}: {token_count}", verbose)
                        except Exception as e:
                            record['token_count'] = ''
                            log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                    else:
                        record['token_count'] = ''
                    # Ensure textracted is last column
                    record = {k: record[k] for k in ['relative_path', 'filename', 'extension']} | {'textracted': record['textracted'], 'token_count': record['token_count']}
                    records.append(record)
                    continue
                # If txt file exists, mark as extracted - regardless of convert flag
                if txt_path.exists():
                    log_event(f"PDF already extracted: {txt_path}", verbose)
                    textracted = True
                    if tokenize:
                        try:
                            token_count = count_tokens(txt_path)
                        except Exception as e:
                            log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                            token_count = ''
                    else:
                        token_count = ''
                else:
                    # Try extraction only if convert flag is set
                    if convert:
                        try:
                            txt_dir.mkdir(parents=True, exist_ok=True)
                            # Extract text from PDF and save to txt file
                            success = extract_and_save(abs_file_path, txt_path)
                            if success:
                                log_event(f"PDF extracted to {txt_path}", verbose)
                                textracted = True
                                if tokenize:
                                    try:
                                        token_count = count_tokens(txt_path)
                                    except Exception as e:
                                        log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                                        token_count = ''
                                else:
                                    token_count = ''
                            else:
                                textracted = False
                                token_count = ''
                        except Exception as e:
                            log_event(f"[ERROR] Exception during PDF extraction: {txt_path} | {e}", verbose)
                            textracted = False
                            token_count = ''
                    else:
                        # Skip extraction when convert flag is not set
                        log_event(f"PDF extraction skipped (--convert not set): {abs_file_path}", verbose)
                        textracted = False
                        token_count = ''
                    record['textracted'] = textracted
                record['token_count'] = token_count
            elif extension.lower() == 'md':
                # Handle MD file conversion only if convert flag is set
                txt_path = Path(dirpath) / (name + '.txt')
                if convert:
                    try:
                        # Convert MD to TXT
                        converted_path = convert_md_to_txt(str(abs_file_path))
                        log_event(f"MD converted to TXT at {converted_path}", verbose)
                        record['textracted'] = True
                        # Count tokens if needed
                        if tokenize and txt_path.exists():
                            try:
                                token_count = count_tokens(txt_path)
                                record['token_count'] = token_count
                            except Exception as e:
                                log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                                record['token_count'] = ''
                        else:
                            record['token_count'] = ''
                    except Exception as e:
                        log_event(f"[ERROR] Exception during MD conversion: {abs_file_path} | {e}", verbose)
                        record['textracted'] = False
                        record['token_count'] = ''
                else:
                    # Skip conversion when convert flag is not set
                    log_event(f"MD conversion skipped (--convert not set): {abs_file_path}", verbose)
                    record['textracted'] = False
                    record['token_count'] = ''
            else:
                record['textracted'] = False
                record['token_count'] = ''
            records.append(record)
    # Merge with old catalog, preferring new records
    new_df = pd.DataFrame(records)
    if not new_df.empty:
        updated_catalog = pd.concat([catalog, new_df]).drop_duplicates(
            subset=['relative_path', 'filename', 'extension'], keep='last'
        ).reset_index(drop=True)
    else:
        updated_catalog = catalog.copy()
    # Remove catalog entries for files that no longer exist in the folder tree
    present_keys = set(
        (rec['relative_path'], rec['filename'], rec['extension']) for rec in records
    )
    updated_catalog = updated_catalog[
        updated_catalog.apply(
            lambda row: (row['relative_path'], row['filename'], row['extension']) in present_keys,
            axis=1
        )
    ].reset_index(drop=True)
    log_event("[END] scan_and_update_catalog", verbose)
    return updated_catalog

    """
    Scan root recursively, append only new files to catalog, and preserve token_count for existing files. Never overwrite or clear token_count for files already present in the catalog. Remove catalog rows for files missing from disk.
    """
    from core.log_utils import log_event
    if excluded_files is None:
        excluded_files = set()
    # Build a set of all files currently on disk
    disk_files = set()
    records = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            abs_fp = Path(dirpath) / fname
            if is_excluded(abs_fp, excluded_files, root):
                continue
            rel_fp = abs_fp.relative_to(root)
            ext = get_file_extension(fname)
            # Skip .txt files in textracted folders
            if ext.lower() == "txt" and extract_folder in abs_fp.parts:
                continue
            disk_files.add((str(rel_fp), fname, ext))
            # Check if this file already exists in the catalog
            mask = (
                (catalog['relative_path'] == str(rel_fp)) &
                (catalog['filename'] == fname) &
                (catalog['extension'] == ext)
            )
            if mask.any():
                # Already catalogued, preserve row as-is
                continue
            # New file: build record
            record = {
                'relative_path': str(rel_fp),
                'filename': fname,
                'extension': ext,
                'textracted': False,
                'token_count': ''
            }
            
            # For PDFs, check if there's a matching txt file in the textracted folder
            # This should happen regardless of whether --convert flag is set
            if ext.lower() == "pdf":
                # Determine top-level folder
                pdf_rel = Path(str(rel_fp))
                parts = pdf_rel.parts
                if len(parts) > 1:
                    top_level = parts[0]
                    txt_path = root / top_level / extract_folder / (Path(fname).stem + '.txt')
                else:
                    # PDF is directly under root
                    txt_path = root / extract_folder / (Path(fname).stem + '.txt')
                    
                # If txt file exists, mark as extracted regardless of convert flag
                if txt_path.exists():
                    from core.log_utils import log_event
                    log_event(f"PDF already extracted: {txt_path}", verbose)
                    record['textracted'] = True
                    if tokenize:
                        try:
                            record['token_count'] = count_tokens(txt_path)
                        except Exception as e:
                            log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
            
            # Tokenize if TXT and requested
            if ext.lower() == "txt" and tokenize:
                try:
                    record['token_count'] = count_tokens(abs_fp)
                except Exception as e:
                    log_event(f"[ERROR] Token counting failed for {abs_fp}: {e}", verbose)
            records.append(record)
    # Append new records to catalog
    if records:
        new_df = pd.DataFrame(records)
        updated_catalog = pd.concat([catalog, new_df], ignore_index=True)
    else:
        updated_catalog = catalog.copy()
    # Remove catalog entries for files no longer on disk
    present_keys = set(disk_files)
    updated_catalog = updated_catalog[
        updated_catalog.apply(
            lambda row: (row['relative_path'], row['filename'], row['extension']) in present_keys,
            axis=1
        )
    ].reset_index(drop=True)

    # Fill in missing token_count if requested
    if tokenize:
        for idx, row in updated_catalog.iterrows():
            if (row['extension'].lower() == 'txt') and (not row['token_count'] or str(row['token_count']).strip() == ''):
                abs_fp = root / row['relative_path']
                try:
                    updated_catalog.at[idx, 'token_count'] = count_tokens(abs_fp)
                except Exception as e:
                    log_event(f"[ERROR] Token counting failed for {abs_fp}: {e}", verbose)

    return updated_catalog

    """
    Scan the root directory recursively, cataloging all files except system files and .txt files in any textracted folder. Extract text from PDFs, and convert Markdown files to TXT.

    Extraction Rule:
        - For any PDF under root/X/... its .txt is saved to root/X/textracted/filename.txt (where X is the first-level subdir).
        - For PDFs directly under root, use root/textracted/filename.txt.
        - For Markdown (.md) files, convert to .txt in the same directory (not in textracted).
        - For non-PDF/non-MD files, catalog but do not extract. Skip system files (e.g., .DS_Store) and all .txt files in textracted folders.
        - Extraction status for PDFs is based solely on .txt presence in the correct textracted folder. Extraction status for MDs is based on .txt presence in the same folder.
    Tokenization is only performed if tokenize=True.

    Args:
        root (Path): Root directory to scan.
        extract_folder (str): Name of the extraction folder (e.g., 'textracted').
        catalog (pd.DataFrame): Existing catalog DataFrame.
        tokenize (bool): If True, count tokens in TXT files; otherwise, skip token counting.

    Returns:
        pd.DataFrame: Updated catalog DataFrame with all files and extraction status for PDFs.
    """
    records = []
    for dirpath, dirs, files in os.walk(root):
        # Skip textracted folders entirely for cataloging
        if os.path.basename(dirpath) == extract_folder:
            continue
        if extract_folder in dirs:
            dirs.remove(extract_folder)
        for f in files:
            abs_file_path = Path(dirpath) / f
            if f in EXCLUDED_FILES:
                from core.log_utils import log_event
                log_event(f"File skipped (excluded): {abs_file_path}", verbose)
                continue
            # Exclusion logic: skip if file or any parent is excluded
            if excluded_files and is_excluded(abs_file_path, excluded_files, root):
                from core.log_utils import log_event
                log_event(f"File skipped (excluded by config): {abs_file_path}", verbose)
                continue
            name, ext = os.path.splitext(f)
            rel_dir = os.path.relpath(dirpath, root)
            extension = get_file_extension(f)
            # Do not catalog .txt files in any textracted folder
            if extension.lower() == 'txt' and extract_folder in Path(dirpath).parts:
                from core.log_utils import log_event
                log_event(f"File skipped (.txt in textracted): {abs_file_path}", verbose)
                continue
            record = {
                'relative_path': rel_dir,
                'filename': name,
                'extension': extension
            }
            if extension.lower() == 'pdf':
                # Compute correct textracted folder
                first_level = get_first_level_subdir(root, abs_file_path)
                txt_dir = first_level / extract_folder
                txt_path = txt_dir / (name + '.txt')
                already_in_catalog = (
                    (catalog['relative_path'] == rel_dir)
                    & (catalog['filename'] == name)
                    & (catalog['extension'] == ext.lstrip('.'))
                )
                skip_due_to_catalog = False
                if already_in_catalog.any():
                    # Already catalogued, check if extracted
                    textracted = catalog.loc[already_in_catalog, 'textracted'].iloc[0]
                    # Only skip if both catalog says extracted AND the .txt file actually exists
                    if (textracted == True or textracted == 'True') and txt_path.exists():
                        skip_due_to_catalog = True
                if skip_due_to_catalog:
                    from core.log_utils import log_event
                    log_event(f"File skipped (already extracted): {abs_file_path}", verbose)
                    record['textracted'] = True
                    if tokenize:
                        try:
                            token_count = count_tokens(str(txt_path))
                            record['token_count'] = token_count
                            from core.log_utils import log_event
                            log_event(f"Token count for {txt_path}: {token_count}", verbose)
                        except Exception as e:
                            record['token_count'] = ''
                            from core.log_utils import log_event
                            log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                    else:
                        record['token_count'] = ''
                    # Ensure textracted is last column
                    record = {k: record[k] for k in ['relative_path', 'filename', 'extension']} | {'textracted': record['textracted'], 'token_count': record['token_count']}
                    records.append(record)
                    continue
                # If txt file exists, mark as extracted - regardless of convert flag
                if txt_path.exists():
                    from core.log_utils import log_event
                    log_event(f"PDF already extracted: {txt_path}", verbose)
                    textracted = True
                    if tokenize:
                        try:
                            token_count = count_tokens(txt_path)
                        except Exception as e:
                            log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                            token_count = ''
                    else:
                        token_count = ''
                else:
                    # Try extraction only if convert flag is set
                    if convert:
                        try:
                            txt_dir.mkdir(parents=True, exist_ok=True)
                            # Extract text from PDF and save to txt file
                            success = extract_and_save(abs_file_path, txt_path)
                            if success:
                                from core.log_utils import log_event
                                log_event(f"PDF extracted to {txt_path}", verbose)
                                textracted = True
                                if tokenize:
                                    try:
                                        token_count = count_tokens(txt_path)
                                    except Exception as e:
                                        log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                                        token_count = ''
                                else:
                                    token_count = ''
                            else:
                                textracted = False
                                token_count = ''
                        except Exception as e:
                            from core.log_utils import log_event
                            log_event(f"[ERROR] Exception during PDF extraction: {txt_path} | {e}", verbose)
                            textracted = False
                            token_count = ''
                    else:
                        # Skip extraction when convert flag is not set
                        from core.log_utils import log_event
                        log_event(f"PDF extraction skipped (--convert not set): {abs_file_path}", verbose)
                        textracted = False
                        token_count = ''
                    record['textracted'] = textracted
                record['token_count'] = token_count
            elif extension.lower() == 'md':
                # Handle MD file conversion only if convert flag is set
                txt_path = Path(dirpath) / (name + '.txt')
                if convert:
                    try:
                        # Convert MD to TXT
                        converted_path = convert_md_to_txt(str(abs_file_path))
                        from core.log_utils import log_event
                        log_event(f"MD converted to TXT at {converted_path}", verbose)
                        record['textracted'] = True
                        
                        # Count tokens if needed
                        if tokenize and txt_path.exists():
                            try:
                                token_count = count_tokens(txt_path)
                                record['token_count'] = token_count
                            except Exception as e:
                                log_event(f"[ERROR] Token counting failed for {txt_path}: {e}", verbose)
                                record['token_count'] = ''
                        else:
                            record['token_count'] = ''
                    except Exception as e:
                        from core.log_utils import log_event
                        log_event(f"[ERROR] Exception during MD conversion: {abs_file_path} | {e}", verbose)
                        record['textracted'] = False
                        record['token_count'] = ''
                else:
                    # Skip conversion when convert flag is not set
                    from core.log_utils import log_event
                    log_event(f"MD conversion skipped (--convert not set): {abs_file_path}", verbose)
                    record['textracted'] = False
                    record['token_count'] = ''
            else:
                record['textracted'] = False
                record['token_count'] = ''
            records.append(record)
    # Merge with old catalog, preferring new records
    new_df = pd.DataFrame(records)
    if not new_df.empty:
        updated_catalog = pd.concat([catalog, new_df]).drop_duplicates(
            subset=['relative_path', 'filename', 'extension'], keep='last'
        ).reset_index(drop=True)
    else:
        updated_catalog = catalog.copy()

    # T3.10: Remove catalog entries for files that no longer exist in the folder tree
    # Build a set of all (relative_path, filename, extension) present in the current scan
    present_keys = set(
        (rec['relative_path'], rec['filename'], rec['extension']) for rec in records
    )
    updated_catalog = updated_catalog[
        updated_catalog.apply(
            lambda row: (row['relative_path'], row['filename'], row['extension']) in present_keys,
            axis=1
        )
    ].reset_index(drop=True)
    return updated_catalog

def save_catalog(catalog: pd.DataFrame, root: Path, catalog_folder: str, verbose: bool = False):
    """
    Purpose: Save catalog DataFrame to CSV.
    Inputs: catalog (pd.DataFrame), root (Path), catalog_folder (str), verbose (bool)
    Outputs: None
    Role: Persists the catalog for inspection and incremental runs. All logging is handled via log_utils.py.
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / 'latest-catalog.csv'
    catalog.to_csv(catalog_path, index=False)
    from core.log_utils import log_event
    log_event(f"Catalog updated at {catalog_path}", verbose)


from core.log_utils import log_event

def run_catalog_workflow(config_path: Path, verbose: bool = False, tokenize: bool = False, force_new: bool = False, convert: bool = False):
    """
    Purpose: Main entry for catalog management and extraction.
    Inputs: config_path (Path), verbose (bool), tokenize (bool), force_new (bool), convert (bool)
    Outputs: None
    Role: Loads config, manages catalog, triggers extraction. All logging is handled via log_utils.py.
    Tokenization is only performed if tokenize=True.
    Text extraction and conversion only occur if convert=True.
    If force_new is True, always create a new catalog from scratch.
    """
    config = load_config(config_path)
    catalog_dir = config['root'] / config['catalog_folder']
    catalog_path = catalog_dir / 'latest-catalog.csv'
    if force_new:
        # Always create a new empty DataFrame
        cols = ['relative_path', 'filename', 'extension', 'textracted', 'token_count']
        catalog = pd.DataFrame(columns=cols)
        log_event(f"[INFO] Creating new catalog from scratch at {catalog_path}", verbose)
    else:
        catalog = load_or_init_catalog(config['root'], config['catalog_folder'])
        log_event(f"CSV found at {catalog_path}", verbose)
    catalog = scan_and_update_catalog(
        config['root'], config['extract_path'], catalog, config.get('excluded_files', set()), verbose=verbose, tokenize=tokenize, convert=convert
    )
    save_catalog(catalog, config['root'], config['catalog_folder'], verbose=verbose)
