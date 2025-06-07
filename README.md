# Library Manager Lite

Effortlessly manage, search, and analyze thousands of research documents—PDFs, images, text files, and more—with agentic automation and analytics.

---

## Key Features

### 1. Scalable Library Catalog
- Manage 1,000s of documents (PDFs, images, txt, etc.)
- Unified catalog with SQLite as the authoritative store (CSV export is optional)
- Incremental updates: only new or changed files are scanned using last_modified and SHA-256
- Always-on SHA-256 hashing for robust duplicate detection
- Profile-driven configuration for all paths, folders, and exclusions
- Automatic conversion: PDFs to TXT, MD to TXT, VTT to TXT (always on)
- Tokenization of TXT files is opt-in via --tokenize
- Robust timestamped database backup via --backupdb

### 2. Modular CLI Workflows
- `catalog.py`: Main entry for cataloging, searching, backup, and CSV export
- `identify.py`: Dedicated workflow for PDF renaming in buffer folders
- `transcribe.py`: Dedicated workflow for YouTube transcript download and catalog update
- `recommend.py`: Agentic recommendations—search and suggest relevant books/files using LLMs
- All workflows are profile-driven and modular

### 3. Multi-Library Profiles & Default Selection
- Seamlessly manage multiple libraries using profiles
- Instantly switch libraries for different projects or contexts
- Set your default library via a `.env` file

### 4. Fast SQLite Search & Analytics
- Directly search your library using SQL queries or CLI search
- Multi-term search (semicolon-separated) supported
- Analytics tools help you understand your library's composition and usage

### 5. Duplicate Detection
- Find exact duplicates using SHA-256 hashing
- Catch near-duplicates with fuzzy Levenshtein distance matching

---

## Installation

```bash
pip install -r requirements.txt
```
- Python 3.10+
- All dependencies are pinned in `requirements.txt`

---

## Quickstart

1. **Set up your library:**
   - Edit your `.env` file to set `DEFAULT_PROFILE=your_profile_name`
   - Define multiple profiles for different libraries in `user_inputs/folder_paths.json`

2. **Incrementally scan and catalog your documents:**
   ```bash
   python catalog.py --profile research
   ```

3. **Auto-rename PDFs in your buffer folder:**
   ```bash
   python identify.py --profile default
   ```

4. **Search your library with multiple keywords:**
   ```bash
   python catalog.py --search --profile research
   ```

5. **Download YouTube transcripts and update catalog:**
   ```bash
   python transcribe.py --profile sandbox
   ```

6. **Get agentic recommendations:**
   ```bash
   python recommend.py --profile research --query "large language models"
   ```

7. **Find duplicates:**
   ```bash
   python catalog.py --find-duplicates --profile sandbox
   ```

8. **Backup your SQLite catalog:**
   ```bash
   python catalog.py --backupdb --profile research
   ```

### CLI Flags & Scripts

| Flag         | Script(s)      | Description                                                                                 |
|--------------|----------------|---------------------------------------------------------------------------------------------|
| --search     | catalog.py     | Search filenames in the SQLite database; supports multi-term queries (semicolon-separated).  |
| --tokenize   | catalog.py     | Count tokens in TXT files and add to catalog (opt-in, default off)                           |
| --convert    | catalog.py     | Convert PDFs/MD/VTT to TXT (always on for new/changed files)                                 |
| --backupdb   | catalog.py     | Create timestamped backup of the SQLite database                                             |
| --csv        | catalog.py     | Export catalog to CSV (optional)                                                             |
| --identify   | identify.py    | Rename PDFs in buffer_folder using LLM                                                       |
| --transcribe | transcribe.py  | Download YouTube transcripts, convert VTT to TXT, update catalog                             |
| --recommend  | recommend.py   | Agentic recommendations for relevant books/files using LLMs                                   |
| --profile    | all            | Select profile from user_inputs/folder_paths.json or .env                                    |
| --verbose    | all            | Enable verbose logging to catalog_folder/logs.txt                                             |

---

## Configuration

- **`.env` file:**
  - Set `DEFAULT_PROFILE=your_profile_name`
  - Other options: library root path, analytics settings
- **Profiles:**
  - Define multiple profiles in `user_inputs/folder_paths.json` to manage different libraries
  - Switch profiles using the `--profile` flag or by changing `.env`

---

## Catalog & Analytics

- Catalog is stored as SQLite (source of truth); CSV export is optional
- Tracks metadata: relative path, filename, extension, last_modified, file_size, textracted, token_count, sha256
- Analytics and search tools help you understand your library's composition and usage
- All actions and errors are logged to catalog_folder/logs.txt for audit

---

## License

MIT License. See `LICENSE` for details.
