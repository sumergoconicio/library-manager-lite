"""
core/catalog_files.py | Catalog Management Module
Purpose: Efficiently scan root folder for PDFs and all files, update and incrementally maintain catalog in SQLite (primary store), trigger extraction as needed, and ensure robust PDF–TXT association. Optionally generate CSV. SHA-256 is always tracked. Directory scanning is optimized for incremental updates.
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-07
Non-Std Deps: pandas, tiktoken, sqlite3
Abstract Spec: Recursively scan root, catalog all files except system/excluded files. For each file, update or insert only if changed (by last_modified or sha256). Remove records for missing files. SQLite is the source of truth; CSV is optional. Always track sha256.
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
    catalog_folder = Path(config['catalog_folder'])
    extract_path = config.get('extract_path', 'PDFextracts')
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
    Purpose: Load existing catalog from SQLite (preferred), or initialize new DataFrame if not found.
    Inputs: root (Path), catalog_folder (str)
    Outputs: catalog (pd.DataFrame)
    Role: Ensures catalog is always available for update. SQLite is primary store.
    """
    import sqlite3
    catalog_dir = catalog_folder
    db_path = catalog_dir / 'library.sqlite'
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            catalog = pd.read_sql("SELECT * FROM catalog", conn)
            conn.close()
            return catalog
        except Exception as e:
            print(f"[ERROR] Failed to load from SQLite: {e}")
    # fallback to empty DataFrame
    cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count', 'sha256']
    return pd.DataFrame(columns=cols)
    """
    Purpose: Load existing catalog or initialize new DataFrame.
    Inputs: root (Path), catalog_folder (str)
    Outputs: catalog (pd.DataFrame)
    Role: Ensures catalog is always available for update.
    """
    catalog_dir = catalog_folder
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
    """
    Purpose: Scan files, update catalog, and (when convert=True) convert .md and .pdf files to .txt if not already present.
    Inputs: root (Path), extract_folder (str), catalog (DataFrame), excluded_files (set), verbose (bool), tokenize (bool), convert (bool)
    Outputs: Updated catalog DataFrame
    Role: Core catalog and conversion routine. When convert=True, ensures all .md and .pdf files are converted to .txt as needed.
    """
    from core.log_utils import log_event
    from ports.convertMDtoTXT import convert_md_to_txt
    from core.extract_text import extract_and_save
    log_event("[START] scan_and_update_catalog", verbose)

    if excluded_files is None:
        excluded_files = set()
    records = []

    import hashlib

    def _sha256_for_file(path):
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            log_event(f"[ERROR] SHA-256 failed for {path}: {e}", verbose)
            return ''

    # --- Step 1: Build mapping of all .txt in any extract_folder folders ---
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
            # Extra: log if .txt in any extract_folder folder
            if os.path.splitext(f)[1].lower() == '.txt' and (
                extract_folder in Path(dirpath).parts or Path(dirpath).name == extract_folder
            ):
                log_event(f"[DEBUG] Found TXT in {extract_folder}: {abs_file_path} (rel_dir={os.path.relpath(dirpath, root)})", verbose)

            if f in EXCLUDED_FILES:
                log_event(f"File skipped (excluded): {abs_file_path}", verbose)
                continue

            if excluded_files and is_excluded(abs_file_path, excluded_files, root):
                log_event(f"File skipped (excluded by config): {abs_file_path}", verbose)
                continue

            name, ext = os.path.splitext(f)
            rel_dir = os.path.relpath(dirpath, root)
            extension = get_file_extension(f)

            # --- Conversion logic: convert .md and .pdf to .txt if needed ---
            if convert:
                # For .md files: convert to .txt in same folder if not present
                if extension.lower() == 'md':
                    txt_path = Path(dirpath) / (name + '.txt')
                    if not txt_path.exists():
                        try:
                            convert_md_to_txt(str(abs_file_path), verbose=verbose)
                            log_event(f"[CONVERT] Converted MD to TXT: {abs_file_path} -> {txt_path}", verbose)
                        except Exception as e:
                            log_event(f"[ERROR] Failed to convert MD: {abs_file_path}: {e}", verbose)
                # For .pdf files: extract text to extract_folder if not present
                elif extension.lower() == 'pdf':
                    # Place extracted .txt in extract_folder under the same top-level
                    rel_parts = Path(rel_dir).parts if rel_dir != '.' else ()
                    top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
                    # Build textracted path: root/top_level/extract_folder/name.txt
                    extract_dir = root / top_level / extract_folder
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    txt_path = extract_dir / (name + '.txt')
                    if not txt_path.exists():
                        try:
                            extract_and_save(abs_file_path, txt_path, verbose=verbose)
                            log_event(f"[CONVERT] Extracted PDF to TXT: {abs_file_path} -> {txt_path}", verbose)
                            # --- Update txt_mapping for immediate detection ---
                            rel2 = os.path.relpath(extract_dir, root)
                            parts2 = Path(rel2).parts if rel2 != '.' else ()
                            mtop = parts2[0] if len(parts2) > 0 else '.'
                            txt_mapping[(mtop, name)] = txt_path
                        except Exception as e:
                            log_event(f"[ERROR] Failed to extract PDF: {abs_file_path}: {e}", verbose)

            # --- NEW: Catalog .txt files in extract_folder folders ---
            in_textracted = (
                extract_folder in Path(dirpath).parts or Path(dirpath).name == extract_folder
            )
            try:
                last_modified = os.path.getmtime(abs_file_path)
                last_modified_str = pd.to_datetime(last_modified, unit='s').strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                last_modified_str = ''
                log_event(f"[ERROR] Could not get last_modified for {abs_file_path}: {e}", verbose)
            # Calculate file_size_in_MB for all files by default
            file_size_in_MB = get_file_size_in_mb(abs_file_path)

            # Always catalog .txt files in any extract_folder folder (including root/extract_folder)
            if extension.lower() == 'txt' and (
                extract_folder in Path(dirpath).parts or Path(dirpath).name == extract_folder
            ):
                rel_parts = Path(rel_dir).parts if rel_dir != '.' else ()
                if rel_dir == extract_folder:
                    top_level = extract_folder
                else:
                    top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
                pdf_match = catalog[
                    (catalog['relative_path'].str.split(os.sep).str[0] == top_level)
                    & (catalog['filename'] == name)
                    & (catalog['extension'].str.lower() == 'pdf')
                ]
                if not pdf_match.empty:
                    file_size_in_MB = ''
                # Always mark as textracted and ensure record is added
                record = {
                    'relative_path': rel_dir,
                    'filename': name,
                    'extension': extension,
                    'last_modified': pd.to_datetime(os.path.getmtime(abs_file_path), unit='s').strftime('%Y-%m-%d %H:%M:%S'),
                    'file_size_in_MB': file_size_in_MB,
                    'textracted': True,
                    'token_count': '',
                    'sha256': ''
                }
                if tokenize:
                    log_event(f"[DEBUG] About to count tokens for TXT: {abs_file_path}", verbose)
                    try:
                        token_count = count_tokens(str(abs_file_path))
                        record['token_count'] = token_count
                    except Exception as e:
                        record['token_count'] = ''
                        log_event(f"[ERROR] Token counting failed for {abs_file_path}: {e}", verbose)
                records.append(record)
                log_event(f"[DEBUG] Appended TXT record: rel_path={record['relative_path']} filename={record['filename']} textracted={record['textracted']}", verbose)
                continue  # Prevent duplicate record for same file

            record = {
                'relative_path': rel_dir,
                'filename': name,
                'extension': extension,
                'last_modified': pd.to_datetime(os.path.getmtime(abs_file_path), unit='s').strftime('%Y-%m-%d %H:%M:%S'),
                'file_size_in_MB': file_size_in_MB,
                'textracted': False,
                'token_count': '',
                'sha256': _sha256_for_file(abs_file_path)
            }

            # --- PDF logic: set textracted if mapping exists ---
            rel_parts = Path(rel_dir).parts if rel_dir != '.' else ()
            top_level = rel_parts[0] if len(rel_parts) > 0 else '.'
            if extension.lower() == 'pdf':
                # If PDF is in root, look for .txt in (extract_folder, name)
                if rel_dir == '.':
                    key = (extract_folder, name)
                else:
                    key = (top_level, name)
                if key in txt_mapping:
                    record['textracted'] = True
                    if tokenize:
                        txt_path = txt_mapping[key]
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

            # --- TXT in extract_folder: always catalog, always tokenize if flag set ---
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
    ordered_cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count', 'sha256']
    for col in ordered_cols:
        if col not in new_df.columns:
            new_df[col] = ''
    new_df = new_df[ordered_cols]

    #if verbose:
    #    print(f"[DEBUG] New catalog entries:\n{new_df.head()}")

    # --- Merge with old catalog, preferring new records ---
    dfs = [df for df in [catalog, new_df] if not df.empty]
    if dfs:
        updated_catalog = pd.concat(dfs).drop_duplicates(
            subset=['relative_path', 'filename', 'extension'], keep='last'
        ).reset_index(drop=True)
    else:
        # Both are empty
        updated_catalog = pd.DataFrame(columns=[
            'relative_path', 'filename', 'extension', 'last_modified',
            'file_size_in_MB', 'textracted', 'token_count', 'sha256'])

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


def save_catalog(catalog: pd.DataFrame, root: Path, catalog_folder: str, verbose: bool = False, backup_db: bool = False, save_csv: bool = False, force_new: bool = False):
    """
    Purpose: Save catalog DataFrame to CSV and SQLite, ensuring required column order.
    Inputs: catalog (pd.DataFrame), root (Path), catalog_folder (str), verbose (bool), backup_db (bool)
    Outputs: None
    Role: Persists the catalog for inspection and incremental runs. All logging is handled via log_utils.py.
    """
    catalog_dir = root / catalog_folder
    catalog_dir.mkdir(parents=True, exist_ok=True)
    ordered_cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count', 'sha256']
    for col in ordered_cols:
        if col not in catalog.columns:
            catalog[col] = ''
    catalog = catalog[ordered_cols]
    # Save to CSV only if requested
    if save_csv:
        catalog_path = catalog_dir / 'latest-catalog.csv'
        catalog.to_csv(catalog_path, index=False)
        log_event(f"Catalog updated at {catalog_path}", verbose)
    # Always save to SQLite
    from adapters.save_to_sqlite import save_dataframe_to_sqlite
    save_dataframe_to_sqlite(catalog, root, catalog_folder, verbose=verbose, backup_db=backup_db, force_new=force_new)


from core.log_utils import log_event

def run_catalog_workflow(profile_config: dict, verbose: bool = False, tokenize: bool = False, force_new: bool = False, convert: bool = False, backup_db: bool = False, save_csv: bool = False):
    """
    Purpose: Main entry for catalog management and extraction.
    Inputs: profile_config (dict from user_inputs/folder_paths.json), verbose (bool), tokenize (bool), force_new (bool), convert (bool), backup_db (bool)
    Outputs: None
    Role: All path variables are sourced from the active profile in user_inputs/folder_paths.json. No hardcoded defaults.
    """
    from core.log_utils import set_log_path
    # Extract all relevant paths from profile
    root = Path(profile_config['root_folder_path'])
    catalog_folder = Path(profile_config['catalog_folder'])
    extract_path = profile_config['extract_path']
    buffer_folder = profile_config.get('buffer_folder', '')
    yt_transcripts_folder = profile_config.get('yt_transcripts_folder', '')
    excluded_files = set(profile_config.get('excluded_files', []))
    log_path = catalog_folder / 'logs.txt'
    set_log_path(str(log_path))
    
    # Create config dict in the format expected by other functions
    config = {
        'root': root,
        'catalog_folder': catalog_folder,
        'extract_path': extract_path,
        'excluded_files': excluded_files
    }
    
    catalog_dir = catalog_folder
    catalog_path = catalog_dir / 'latest-catalog.csv'
    if force_new:
        # Always create a new empty DataFrame
        cols = ['relative_path', 'filename', 'extension', 'last_modified', 'file_size_in_MB', 'textracted', 'token_count', 'sha256']
        catalog = pd.DataFrame(columns=cols)
        log_event(f"[INFO] Creating new catalog from scratch at {catalog_path}", verbose)
    else:
        catalog = load_or_init_catalog(root, catalog_folder)
        log_event(f"[INFO] Loaded catalog from SQLite or initialized new DataFrame", verbose)
    catalog = scan_and_update_catalog(
        root, extract_path, catalog, excluded_files, verbose=verbose, tokenize=tokenize, convert=convert
    )
    save_catalog(catalog, root, catalog_folder, verbose=verbose, backup_db=backup_db, save_csv=save_csv, force_new=force_new)
