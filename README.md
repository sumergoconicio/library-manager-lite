# Library Manager Lite

**Bulk PDF Text Extraction & Cataloguing Tool**

## Overview
Library Manager Lite is a modular, auditable tool for extracting text from PDFs, cataloguing files, counting tokens in TXT files, analyzing file collections, and downloading YouTube transcripts. Designed for reproducibility and compliance with project rules.

## Features
- Bulk PDF text extraction (PyMuPDF)
- Incremental cataloguing (CSV and SQLite)
- Token counting for TXT files using heuristic estimation
- MD to TXT conversion
- VTT subtitle to TXT conversion
- Exclusion logic via config
- Unified logging with verbose mode
- CLI flags for all major workflows
- Comprehensive catalog analysis with folder-level and extension-level breakdowns
- File size tracking and analysis with precise formatting
- YouTube transcript downloading with automatic VTT to TXT conversion
- SQLite database integration for robust data storage and querying

## Usage
Run from the command line:

```sh
python main.py [--recatalog] [--analysis] [--verbose] [--tokenize] [--identify] [--transcribe] [--backupdb]
```

- `--recatalog`: Regenerate catalog from scratch (automatically includes text conversion and tokenization)
- `--analysis`: Output summary analysis to latest-breakdown.txt
- `--verbose`: Log every process iteration
- `--tokenize`: Count tokens in TXT files and add to catalog
- `--convert`: Convert PDFs to TXT, MD files to TXT, and VTT files to TXT
- `--identify`: Rename PDFs in buffer_folder using LLM
- `--transcribe`: Download transcripts from YouTube videos/playlists, convert VTT to TXT, and automatically run incremental catalog update with token counting enabled
- `--backupdb`: Create a timestamped backup of the SQLite database after saving the catalog
- `--profile`: Select library profile to use (from folder_paths.json)

## Configuration
### Library Profiles
Edit `user_inputs/folder_paths.json` to set multiple library profiles. Each profile is a top-level key with its own configuration:

```json
{
  "hoard": {
    "root_folder_path": "/path/to/main/library",
    "catalog_folder": "_catalog",
    ...
  },
  "sandbox": {
    "root_folder_path": "/path/to/test/library",
    "catalog_folder": "_catalog",
    ...
  }
}
```

Each profile contains:
- `root_folder_path`: Absolute path to your files
- `catalog_folder` (default: _catalog)
- `extract_path` (default: textracted)
- `excluded_files` (list of files/folders to skip)
- `buffer_folder` (folder containing PDFs to rename)
- `yt_transcripts_folder` (folder to save YouTube transcripts)

### Profile Selection
Select a profile using one of these methods (in order of precedence):
1. CLI argument: `--profile sandbox`
2. Environment variable: Set `DEFAULT_LIBRARY_PROFILE=hoard` in `.env`
3. Default: Uses the first profile found in the config file

Edit `user_inputs/llm_config.json` to configure LLM providers for different workflows:
- `workflows`: Map workflow names to provider/model configurations
- `defaults`: Default provider/model configuration

## Outputs
- `latest-catalog.csv`: Catalog of all files (CSV format)
- `library.sqlite`: Catalog database (SQLite format) with indexed columns for efficient querying
- `latest-folder-breakdown.csv`: Folder-level analysis with file counts, textracted counts, file sizes (MB with 3 decimal precision), and token counts
- `latest-extension-breakdown.csv`: Extension-type analysis with file counts per extension
- `logs.txt`: Process log (if verbose)

## Requirements
- Python 3.10+
- pandas==2.2.2
- PyMuPDF==1.22.5
- litellm==1.27.6
- yt-dlp==2023.11.16
- pytest==8.2.0 (testing)

## Environment Variables
Set these in your environment or in a `.env` file in the project root:
- API keys for LLM providers as specified in `user_inputs/llm_config.json`
  - Example: `ANTHROPIC_API_KEY=your_api_key_here`
  - Example: `OPENAI_API_KEY=your_api_key_here`
- `DEFAULT_LIBRARY_PROFILE`: Profile to use from folder_paths.json if not specified via CLI
  - Example: `DEFAULT_LIBRARY_PROFILE=hoard`
- See `user_inputs/llm_provider_usage.md` for more details

## Project Structure
- `main.py`: CLI entry point, workflow orchestration
- `core/`: Business logic (catalog management, text extraction, token counting)
- `ports/`: Interface adapters (format conversions, profile loading)
- `adapters/`: External service implementations (LLM providers, SQLite, YouTube)
- `user_inputs/`: Configuration files (folder paths, LLM settings)

See `dev/architecture.md` and `dev/project-brief.md` for detailed module responsibilities and data flow.

---

_Compliant with all requirements as of Sprint 28 (2025-06-06)._


> **CLI tool for cataloging all files and extracting text from PDFs in large folder trees.**

---

## Features

- 📁 Catalogs **all files** (not just PDFs) into a robust CSV inventory (excluding .txt files in `textracted` folders)
- 🗂️ **Skips system files** (e.g. .DS_Store, Thumbs.db)
- 📄 **Extracts text from PDFs** to a single `textracted` folder per first-level directory
- 📝 Maintains an up-to-date, auditable catalog for downstream workflows
- 🧩 Modular, standards-driven Python codebase (Hexagonal Architecture)
- ⚡ Fast, idempotent, and CLI-first (no interactive prompts)
- 📺 Downloads transcripts from YouTube videos and playlists

---

## Getting Started

### Prerequisites
- Python 3.9+
- Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration
- Edit `user_inputs/folder_paths.json`:
  - `root_folder_path`: Absolute path to your files
  - `catalog_folder`: (optional) Subfolder for catalog CSV (default: `_catalog`)
  - `extract_path`: (optional) Name for extraction folders (default: `textracted`)
  - `excluded_files`: (optional) List of files or folders to skip during cataloging. Folders must end with `/` (e.g., `Web-Docs/`).
  - `buffer_folder`: (optional) Folder containing PDFs to rename
  - `yt_transcripts_folder`: (optional) Folder to save YouTube transcripts

### Example `folder_paths.json`
```json
{
  "root_folder_path": "/path/to/your/files",
  "catalog_folder": "_catalog",
  "extract_path": "textracted",
  "excluded_files": ["Web-Docs/", "README.md"],
  "buffer_folder": "/path/to/buffer",
  "yt_transcripts_folder": "/path/to/transcripts"
}
```

---

## Usage

From the project root:

```bash
python main.py
```

---

### CLI Flag Stacking and Precedence (2025-05-25)

- Only one main operation runs per invocation: `--identify`, `--recatalog`, `--analysis`, `--transcribe`, or (default) incremental update.
- Modifier flags (`--convert`, `--tokenize`, `--verbose`) stack and modify the main operation.
- If multiple main-operation flags are passed, the first matched in priority order is executed: `--identify` > `--transcribe` > `--recatalog` > `--analysis` > default.
- Mutually exclusive flags are not enforced by argparse; user should avoid passing conflicting main-operation flags.

#### Scenario Table

| Scenario                         | Catalog Mode      | Extraction/Convert | Tokenize | Verbose | Notes                                 |
|-----------------------------------|-------------------|--------------------|----------|---------|---------------------------------------|
| (1) No flags                     | Incremental       | No                 | No       | No      | Only new files catalogued             |
| (2) --recatalog                    | Full rebuild      | Yes                | Yes      | No      | Catalog replaced, convert & tokenize implied |
| (3) --recatalog --convert --tokenize| Full rebuild      | Yes                | Yes      | No      | All features active                   |
| (4) --convert --verbose          | Incremental       | Yes                | No       | Yes     | Extraction + logging, no token count  |

> **Note:** If you pass multiple main-operation flags (e.g., `--recatalog --analysis`), only the first in priority order will run. Modifiers can be freely combined with any main operation.

---

- Scans all subfolders of `root_folder_path`
- Catalogs every file (except system files, excluded files/folders, and .txt files in `textracted` folders) in a CSV
- For each PDF, extracts text to the correct `textracted` folder
- Updates the catalog with extraction status (flagged True if corresponding .txt exists in `textracted`)
- Renames PDFs in `buffer_folder` using LLM (if `--identify` flag is used)

---

## Exclusion Logic

- You can exclude files or folders from cataloging by listing them in `excluded_files` in your config.
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
