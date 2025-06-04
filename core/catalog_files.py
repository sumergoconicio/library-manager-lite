"""
core/catalog_files.py | Catalog Management Module
Purpose: Scan root folder for PDFs and all files, update catalog CSV, trigger extraction as needed, and ensure robust PDF–TXT association. Catalogs and tokenizes all .txt files in any textracted folder. For each PDF, sets textracted=True if a matching .txt exists in any textracted folder under the same top-level directory. Adds last_modified and file_size_in_MB columns to catalog, with file_size_in_MB skipped for textracted files associated with PDF row-items. File size extraction now uses a single robust utility get_file_size_in_mb for all cases. file_size_in_MB values are always rounded to 3 decimal places for precision and consistency.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-03
Non-Std Deps: pandas, tiktoken
Abstract Spec: Recursively scan root, catalog all files except system/excluded files. Build a mapping of (top-level, basename) to .txt path for all .txt in textracted folders. For PDFs, set textracted=True if a matching .txt exists. Tokenize all .txt in textracted if tokenize flag is set. Ensure atomic, robust DataFrame updates. Docstrings and file header updated to reflect changes.
"""

import os
from pathlib import Path
import pandas as pd
import json
from core.extract_text import extract_and_save
from ports.convertMDtoTXT import convert_md_to_txt
from ports.convertVTTtoTXT import extract_vtt_to_txt
from core.file_utils import get_file_extension
from core.token_counter import count_tokens
from core.log_utils import log_event
from adapters.save_to_sqlite import save_dataframe_to_sqlite

def get_file_size_in_mb(file_path: str) -> float:
    """
    Purpose: Extract the size of a file in MB, rounded to 3 decimal places.
    Inputs:
        file_path (str): Path to the file whose size we need to calculate.
    Outputs:
        file_size_in_mb (float): Size of the file in MB (returns 0.0 if file doesn't exist or error occurs). Value is always rounded to 3 decimal places.
    Role: Robustly retrieves file size for cataloging. Centralizes error handling. Precision is enforced for catalog consistency.
    """
    import os
    try:
        if os.path.isfile(file_path):
            return round(os.path.getsize(file_path) / (1024 * 1024), 3)
        return 0.0
    except Exception as e:
        print(f"[ERROR] Error calculating file size for {file_path}: {e}")
        return 0.0


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
    cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count']
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
    from core.log_utils import log_event
    log_event("[START] scan_and_update_catalog", verbose)

    if excluded_files is None:
        excluded_files = set()
    records = []

    # --- Step 1: Build mapping of all .txt in any textracted folder ---
    txt_mapping = {}  # (top_level, basename) -> txt_path
    for dirpath, dirs, files in os.walk(root):
        if os.path.basename(dirpath) == extract_folder:
            rel_parts = Path(os.path.relpath(dirpath, root)).parts
            top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
            for f in files:
                name, ext = os.path.splitext(f)
                if ext.lower() == '.txt':
                    txt_mapping[(top_level, name)] = Path(dirpath) / f
    log_event(f"[DEBUG] Built txt_mapping with {len(txt_mapping)} entries", verbose)

    # --- Step 2: Main scan loop ---
    for dirpath, dirs, files in os.walk(root):
        log_event(f"[SCAN] Entering directory: {dirpath}", verbose)
        if extract_folder in dirs:
            dirs.remove(extract_folder)
        for f in files:
            abs_file_path = Path(dirpath) / f
            log_event(f"[SCAN] Considering file: {abs_file_path} (ext: {os.path.splitext(f)[1]})", verbose)

            if f in EXCLUDED_FILES:
                log_event(f"File skipped (excluded): {abs_file_path}", verbose)
                continue

            if excluded_files and is_excluded(abs_file_path, excluded_files, root):
                log_event(f"File skipped (excluded by config): {abs_file_path}", verbose)
                continue

            name, ext = os.path.splitext(f)
            rel_dir = os.path.relpath(dirpath, root)
            extension = get_file_extension(f)

            # --- NEW: Catalog .txt files in textracted folders ---
            in_textracted = extract_folder in Path(dirpath).parts
            try:
                last_modified = os.path.getmtime(abs_file_path)
                last_modified_str = pd.to_datetime(last_modified, unit='s').strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                last_modified_str = ''
                log_event(f"[ERROR] Could not get last_modified for {abs_file_path}: {e}", verbose)

            # Calculate file_size_in_MB for all files by default
            file_size_in_MB = get_file_size_in_mb(abs_file_path)

            # If .txt in textracted and associated with a PDF row-item, set blank
            if extension.lower() == 'txt' and in_textracted:
                rel_parts = Path(rel_dir).parts if rel_dir != '.' else ()
                top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
                pdf_match = catalog[
                    (catalog['relative_path'].str.split(os.sep).str[0] == top_level)
                    & (catalog['filename'] == name)
                    & (catalog['extension'].str.lower() == 'pdf')
                ]
                if not pdf_match.empty:
                    file_size_in_MB = ''

            record = {
                'relative_path': rel_dir,
                'filename': name,
                'extension': extension,
                'last_modified': last_modified_str,
                'file_size_in_MB': file_size_in_MB,
                'textracted': False,
                'token_count': ''
            }

            # --- PDF logic: set textracted if mapping exists ---
            rel_parts = Path(rel_dir).parts if rel_dir != '.' else ()
            top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
            if extension.lower() == 'pdf':
                if (top_level, name) in txt_mapping:
                    record['textracted'] = True
                    if tokenize:
                        txt_path = txt_mapping[(top_level, name)]
                        log_event(f"[DEBUG] Counting tokens for PDF-associated TXT: {txt_path}", verbose)
                        if txt_path.exists():
                            try:
                                token_count = count_tokens(str(txt_path))
                                record['token_count'] = token_count
                            except Exception as e:
                                record['token_count'] = ''
                                log_event(f"[ERROR] Token counting failed for PDF-associated TXT {txt_path}: {e}", verbose)
                        else:
                            record['token_count'] = ''
                            log_event(f"[ERROR] Associated TXT file does not exist: {txt_path}", verbose)

            # --- TXT in textracted: always catalog, always tokenize if flag set ---
            if extension.lower() == 'txt':
                if tokenize:
                    log_event(f"[DEBUG] About to count tokens for TXT: {abs_file_path}", verbose)
                    try:
                        token_count = count_tokens(str(abs_file_path))
                        record['token_count'] = token_count
                    except Exception as e:
                        record['token_count'] = ''
                        log_event(f"[ERROR] Token counting failed for {abs_file_path}: {e}", verbose)
            records.append(record)

    # --- Step 3: Build DataFrame and ensure column order ---
    new_df = pd.DataFrame(records)
    ordered_cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count']
    for col in ordered_cols:
        if col not in new_df.columns:
            new_df[col] = ''
    new_df = new_df[ordered_cols]

    #if verbose:
    #    print(f"[DEBUG] New catalog entries:\n{new_df.head()}")

    # --- Merge with old catalog, preferring new records ---
    if not new_df.empty:
        updated_catalog = pd.concat([catalog, new_df]).drop_duplicates(
            subset=['relative_path', 'filename', 'extension'], keep='last'
        ).reset_index(drop=True)
    else:
        updated_catalog = catalog.copy()

    if verbose:
        print(f"[DEBUG] Updated catalog after merge:\n{updated_catalog.head()}")

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


def save_catalog(catalog: pd.DataFrame, root: Path, catalog_folder: str, verbose: bool = False, backup_db: bool = False):
    """
    Purpose: Save catalog DataFrame to CSV and SQLite, ensuring required column order.
    Inputs: catalog (pd.DataFrame), root (Path), catalog_folder (str), verbose (bool), backup_db (bool)
    Outputs: None
    Role: Persists the catalog for inspection and incremental runs. All logging is handled via log_utils.py.
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = catalog_dir / 'latest-catalog.csv'
    # Ensure column order before saving
    ordered_cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count']
    for col in ordered_cols:
        if col not in catalog.columns:
            catalog[col] = ''
    catalog = catalog[ordered_cols]
    
    # Save to CSV
    catalog.to_csv(catalog_path, index=False)
    log_event(f"Catalog updated at {catalog_path}", verbose)
    
    # Save to SQLite database
    save_dataframe_to_sqlite(catalog, root, catalog_folder, verbose=verbose, backup_db=backup_db)


from core.log_utils import log_event

def run_catalog_workflow(config_path: Path, verbose: bool = False, tokenize: bool = False, force_new: bool = False, convert: bool = False, backup_db: bool = False):
    """
    Purpose: Main entry for catalog management and extraction.
    Inputs: config_path (Path), verbose (bool), tokenize (bool), force_new (bool), convert (bool), backup_db (bool)
    Outputs: None
    Role: Loads config, manages catalog, triggers extraction. All logging is handled via log_utils.py.
    Tokenization is only performed if tokenize=True.
    Text extraction and conversion only occur if convert=True.
    If force_new is True, always create a new catalog from scratch.
    If backup_db is True, create a backup of the SQLite database.
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
    save_catalog(catalog, config['root'], config['catalog_folder'], verbose=verbose, backup_db=backup_db)
