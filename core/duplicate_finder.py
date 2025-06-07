"""
duplicate_finder.py | Detects potential duplicate files in the catalog
Author: ChAI-Engine
Last-updated: 2025-06-07
Non-std deps: pandas, rapidfuzz
Abstract spec: For each top-level folder in the catalog, find file pairs with identical sizes, then compute token_sort_ratio and Levenshtein distance on filenames. Output results as CSV.
"""

import os
import sys
import argparse
import sqlite3
import itertools
import pandas as pd
from rapidfuzz import fuzz, distance


def _load_exclusions():
    """
    Purpose: Load list of top_level_folders to exclude from duplicate finding.
    Inputs: None
    Outputs: Set of excluded folder names
    Role: Exclusion config loader
    """
    exclusions_path = "user_inputs/duplicate_finder_exclusions.json"
    try:
        with open(exclusions_path, "r") as f:
            data = json.load(f)
        # Accept either a list or a dict with 'exclude' key
        if isinstance(data, dict) and 'exclude' in data:
            return set(data['exclude'])
        elif isinstance(data, list):
            return set(data)
        else:
            return set()
    except Exception:
        return set()

def get_file_records(db_path, exclusions=None):
    """
    Purpose: Fetch file records from SQLite database, skipping excluded top_level_folders.
    Inputs: db_path (str) - path to library.sqlite
            exclusions (set or None) - folders to skip
    Outputs: List of dicts with keys: top_level_folder, filename, file_size, sha256
    Role: Data extraction for duplicate analysis
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT relative_path, filename, file_size_in_MB, sha256 FROM catalog")
    rows = cur.fetchall()
    records = []
    for rel_path, filename, file_size_MB, sha256 in rows:
        top_level = os.path.normpath(rel_path).split(os.sep)[0]
        if exclusions and top_level in exclusions:
            continue
        records.append({
            'top_level_folder': top_level,
            'filename': filename,
            'file_size_MB': file_size_MB,
            'sha256': sha256
        })
    conn.close()
    return records


def find_duplicates(records):
    """
    Purpose: Identify file pairs in the same top-level folder with identical sizes.
    Inputs: records (list of dicts)
    Outputs: List of dicts with duplicate pair info
    Role: Core duplicate detection logic
    """
    results = []
    # Group by top_level_folder
    folders = {}
    for rec in records:
        folders.setdefault(rec['top_level_folder'], []).append(rec)
    for folder, files in folders.items():
        # Group files by file_size_MB
        size_map = {}
        for f in files:
            size_map.setdefault(f['file_size_MB'], []).append(f)
        for size_MB, group in size_map.items():
            if len(group) < 2:
                continue
            # All unique pairs
            for f1, f2 in itertools.combinations(group, 2):
                results.append({
                    'top_level_folder': folder,
                    'filename1': f1['filename'],
                    'filename2': f2['filename'],
                    'file_size_MB': size_MB
                })
    return results


def compute_similarity(pairs):
    """
    Purpose: Compute token_sort_ratio, normalized Levenshtein ratio, and confidence for each file pair.
    Inputs: pairs (list of dicts)
    Outputs: DataFrame with similarity and confidence columns
    Role: Similarity scoring and classification
    """
    data = []
    for pair in pairs:
        fn1 = pair['filename1']
        fn2 = pair['filename2']
        tsr = fuzz.token_sort_ratio(fn1, fn2)
        lev_dist = distance.Levenshtein.distance(fn1, fn2)
        max_len = max(len(fn1), len(fn2)) or 1
        norm_lev = 1 - (lev_dist / max_len)
        # Confidence assignment
        if tsr >= 90 and norm_lev >= 0.85:
            confidence = "high"
        elif tsr >= 80 and norm_lev >= 0.7:
            confidence = "possible"
        else:
            confidence = "unlikely"
        data.append({
            'top_level_folder': pair['top_level_folder'],
            'filename1': fn1,
            'filename2': fn2,
            'file_size_MB': pair['file_size_MB'],
            'token_sort_ratio': tsr,
            'normalized_levenshtein': norm_lev,
            'confidence': confidence
        })
    return pd.DataFrame(data)


import json

def _load_catalog_folder(profile="default"):
    """
    Purpose: Load catalog_folder path from folder_paths.json or folder_paths_example.json.
    Inputs: profile (str) - profile name (default 'default')
    Outputs: catalog_folder (str)
    Role: Config loader for dynamic path resolution
    """
    config_path = "user_inputs/folder_paths.json"
    example_path = "user_inputs/folder_paths_example.json"
    try:
        with open(config_path, "r") as f:
            paths = json.load(f)
    except FileNotFoundError:
        with open(example_path, "r") as f:
            paths = json.load(f)
    if profile not in paths:
        raise KeyError(f"Profile '{profile}' not found in folder_paths config.")
    return paths[profile]["catalog_folder"]

def find_and_save_duplicates(profile="default"):
    """
    Purpose: Find potential duplicate files in the catalog and save results as CSV.
    Inputs:
        profile (str): Profile name for folder_paths.json (default 'default')
    Outputs: Saves CSV file of duplicate candidates to catalog_folder/latest-duplicates.csv
    Role: Callable interface for duplicate detection logic
    """
    catalog_folder = _load_catalog_folder(profile)
    db_path = os.path.join(catalog_folder, "library.sqlite")
    exclusions = _load_exclusions()
    records = get_file_records(db_path, exclusions=exclusions)
    # --- SHA256 exact duplicate detection ---
    from collections import defaultdict
    hash_map = defaultdict(list)
    for rec in records:
        sha = rec.get('sha256')
        if sha and sha.strip():
            hash_map[sha].append(rec)
    exact_pairs = []
    for sha, group in hash_map.items():
        if len(group) < 2:
            continue
        # All unique pairs for this hash
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                r1, r2 = group[i], group[j]
                exact_pairs.append({
                    'top_level_folder': r1['top_level_folder'],
                    'filename1': r1['filename'],
                    'filename2': r2['filename'],
                    'file_size_MB': r1['file_size_MB'],
                    'confidence': 'exact'
                })
    # --- Fuzzy/size duplicate detection as before ---
    pairs = find_duplicates(records)
    df_fuzzy = compute_similarity(pairs)
    # Filter: only keep rows with token_sort_ratio >= 80 AND normalized_levenshtein >= 0.7
    df_fuzzy = df_fuzzy[(df_fuzzy['token_sort_ratio'] >= 80) & (df_fuzzy['normalized_levenshtein'] >= 0.7)]
    # Only output the requested columns
    output_cols = ['top_level_folder', 'filename1', 'filename2', 'file_size_MB', 'confidence']
    df_fuzzy = df_fuzzy[output_cols]
    # Remove fuzzy pairs that are already exact pairs
    exact_set = set((row['top_level_folder'], row['filename1'], row['filename2'], row['file_size_MB']) for row in exact_pairs)
    df_fuzzy = df_fuzzy[~df_fuzzy.apply(lambda row: (row['top_level_folder'], row['filename1'], row['filename2'], row['file_size_MB']) in exact_set, axis=1)]
    # Combine exact and fuzzy
    df_exact = pd.DataFrame(exact_pairs, columns=output_cols)
    df_out = pd.concat([df_exact, df_fuzzy], ignore_index=True)
    out_path = os.path.join(catalog_folder, 'latest-duplicates.csv')
    os.makedirs(catalog_folder, exist_ok=True)
    df_out.to_csv(out_path, index=False)
    print(f"Duplicate candidates written to {out_path}")
