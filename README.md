# Library Manager Lite

**Bulk PDF Text Extraction & Cataloguing Tool**

---

## Overview
Library Manager Lite is a modular, standards-driven CLI tool for:
- Extracting text from PDFs
- Cataloguing and analyzing all files in a directory tree
- Counting tokens in TXT files
- Downloading and archiving YouTube transcripts
- Maintaining robust, auditable inventories (CSV & SQLite)

Designed for reproducibility, compliance, and ease of automation.

---

## Features
- Bulk PDF text extraction (PyMuPDF)
- Incremental cataloguing (CSV and SQLite)
- Token counting for TXT files
- MD/VTT to TXT conversion
- Exclusion logic via config
- Unified logging (with verbose mode)
- CLI flags for all workflows
- Comprehensive catalog analysis
- File size tracking and breakdowns
- YouTube transcript downloading (with VTT to TXT conversion)
- Automatic database backups

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure folders:**
   - Edit `user_inputs/folder_paths.json` (see below)
3. **Run the CLI:**
   ```bash
   python main.py [flags]
   ```

---

## Configuration
- Edit `user_inputs/folder_paths.json` to define one or more library profiles (see example below).
- Each profile includes:
  - `root_folder_path`: Absolute path to your files
  - `catalog_folder`: (optional, default: `_catalog`)
  - `extract_path`: (optional, default: `PDFextracts`)
  - `excluded_files`: (optional) List of files/folders to skip (folders must end with `/`)
  - `buffer_folder`: (optional) PDFs to rename
  - `saved_searches_folder`: (optional, default: `SavedSearches`) Save search results
  - `yt_transcripts_folder`: (optional, default: `YTtranscripts`) Save YouTube transcripts

**Profile selection precedence:**
1. CLI: `--profile <name>`
2. `.env`: `DEFAULT_LIBRARY_PROFILE=<name>`
3. Default: first profile in config

**Example `folder_paths.json`:**
```json
{
  "sandbox": {
    "root_folder_path": "/path/to/files",
    "catalog_folder": "_catalog",
    "extract_path": "textracted",
    "excluded_files": ["Web-Docs/", "README.md"],
    "buffer_folder": "/path/to/buffer",
    "yt_transcripts_folder": "/path/to/transcripts"
  }
}
```

- Configure LLM providers in `user_inputs/llm_config.json` (see that file for details).

---

## Usage

### CLI Flags
| Flag          | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| --search      | Search filenames in the SQLite database; supports multi-term queries (semicolon-separated) |
| --recatalog   | Full catalog rebuild (includes text conversion and tokenization)            |
| --analysis    | Output summary analysis to latest-breakdown.txt                             |
| --verbose     | Log every process iteration                                                 |
| --tokenize    | Count tokens in TXT files and add to catalog                                |
| --convert     | Convert PDFs to TXT, MD files to TXT, and VTT files to TXT                  |
| --identify    | Rename PDFs in buffer_folder using LLM                                      |
| --transcribe  | Download YouTube transcripts, convert VTT to TXT, update catalog            |
| --backupdb    | Create timestamped backup of the SQLite database                            |
| --profile     | Select library profile to use (from folder_paths.json)                      |

- Only one main operation runs per invocation: `--identify`, `--recatalog`, `--analysis`, `--transcribe`, or (default) incremental update.
- Modifier flags (`--convert`, `--tokenize`, `--verbose`) can be combined with any main operation.
- If multiple main-operation flags are passed, the first matched in priority order is executed: `--identify` > `--transcribe` > `--recatalog` > `--analysis` > default.
- Mutually exclusive flags are not enforced by argparse; avoid passing conflicting main-operation flags.

---

## Outputs
- `latest-catalog.csv`: Catalog of all files (CSV format)
- `library.sqlite`: Catalog database (SQLite format)
- `latest-folder-breakdown.csv`: Folder-level analysis
- `latest-extension-breakdown.csv`: Extension-type analysis
- `logs.txt`: Process log (if verbose)
- `SavedSearches/YYYYMMDDHHmmss_searchterm1_searchterm2.csv`: Search results export for multi-term queries (semicolon-separated, OR logic)

**Catalog columns (strict order):**
- Folders to be excluded must end with a `/` (e.g., `Web-Docs/`).
- Any file or folder matching an entry in `excluded_files` will be skipped during catalog generation and extraction.


## Example Output

- `your_root/_catalog/catalog.csv`:

| relative_path | filename | extension | last_modified | file_size | textracted | token_count |
|---------------|----------|-----------|--------------|-----------|------------|-------------|
| 2024/letters  | file1    | pdf       | 2025-06-04   | 2.1       | True       | 12000       |
| 2024/images   | img1     | jpg       | 2025-06-04   | 0.3       |            |             |

_Note: Column order is now strictly enforced as: relative_path, filename, extension, last_modified, file_size, textracted, token_count._


- Extracted text: `your_root/2024/textracted/file1.txt`

---

## YouTube Transcript Downloading

The `--transcribe` flag enables downloading transcripts from YouTube videos and playlists:

```bash
python main.py --transcribe
```

This will:
1. Prompt for a YouTube video or playlist URL
2. Optionally prompt for a subfolder name to organize transcripts
3. Download all available transcripts to the configured `yt_transcripts_folder`
4. Convert VTT files to TXT format and delete the original VTT files
5. Track downloaded videos in `catalog_folder/latest-transcript-archive.csv` to avoid duplicates

Transcripts are saved with filenames based on upload date and video title. The system maintains a CSV archive of all downloaded transcripts with the following information:
- Filename
- YouTube URL
- Date added

This ensures that each video is only downloaded once, even across multiple sessions. The system checks both the filename and video ID to prevent duplicates.

For playlists, each video is processed individually and tracked in the archive.

---

## SQLite Database Integration

As of Sprint 24 (2025-06-04), Library Manager Lite now saves catalog data to a SQLite database alongside the CSV format:

- The catalog is automatically saved to both formats whenever it's updated
- The SQLite database (`library.sqlite`) is stored in the catalog folder
- Catalog analysis now primarily uses the SQLite database for improved performance and query capabilities
- If the SQLite database is unavailable or fails to load, the system falls back to using the CSV file
- This integration provides better data integrity and robustness while maintaining backward compatibility

As of Sprint 25 (2025-06-04), a database backup feature has been added:

- Use the `--backupdb` flag to create timestamped backups of the SQLite database
- Backups are named with format `YYYYMMDDHHmmss.library.sqlite.backup` for easy identification
- Backups are stored in the same catalog folder as the main database
- The backup is created after saving the catalog, ensuring all changes are included
- When combined with `--verbose`, detailed logging of the backup process is provided

This enhancement is completely transparent to users - no additional configuration or commands are needed beyond the optional `--backupdb` flag. The system automatically maintains both storage formats and intelligently selects the best data source for analysis operations.

---

## Transcript Archive

The `transcript_archive.py` module is responsible for managing the transcript archive. It uses a CSV file to keep track of downloaded transcripts and prevents duplicates by checking the filename and video ID.

---

## Troubleshooting
- Make sure all paths in `folder_paths.json` are correct and absolute
- Only PDFs are extracted; other files are just catalogued
- Rerun safely: extraction is idempotent

---

## License

Distributed under the MIT License. See LICENSE for more information.

---
