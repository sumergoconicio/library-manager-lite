# Library Manager Lite

**Bulk PDF Text Extraction & Cataloguing Tool**

## Overview
Library Manager Lite is a modular, auditable tool for extracting text from PDFs, cataloguing files, counting tokens in TXT files, and analyzing file collections. Designed for reproducibility and compliance with project rules.

## Features
- Bulk PDF text extraction (PyMuPDF)
- Incremental cataloguing (CSV)
- Token counting for TXT files (tiktoken)
- MD to TXT conversion
- Exclusion logic via config
- Unified logging with verbose mode
- CLI flags for all major workflows
- Catalog analysis with plain text output

## Usage
Run from the command line:

```sh
python main.py [--catalog] [--analysis] [--verbose] [--tokenize]
```

- `--catalog`: Regenerate catalog from scratch
- `--analysis`: Output summary analysis to latest-breakdown.txt
- `--verbose`: Log every process iteration
- `--tokenize`: Count tokens in TXT files and add to catalog

## Configuration
Edit `user_inputs/folder-paths.json` to set:
- `root_folder_path`
- `catalog_folder` (default: _catalog)
- `extract_folder` (default: textracted)
- `excluded_files` (list of files/folders to skip)

## Outputs
- `latest-catalog.csv`: Catalog of all files
- `latest-breakdown.txt`: Analysis summary
- `logs.txt`: Process log (if verbose)

## Requirements
- Python 3.10+
- pandas==2.2.2
- PyMuPDF==1.22.5
- tiktoken==0.5.1
- pytest==8.2.0 (testing)

## Project Structure
See `dev/architecture.md` and `dev/project-brief.md` for detailed module responsibilities and data flow.

---

_Compliant with all requirements as of Sprint 7 (2025-05-23)._


> **CLI tool for cataloging all files and extracting text from PDFs in large folder trees.**

---

## Features

- 📁 Catalogs **all files** (not just PDFs) into a robust CSV inventory (excluding .txt files in `textracted` folders)
- 🗂️ **Skips system files** (e.g. .DS_Store, Thumbs.db)
- 📄 **Extracts text from PDFs** to a single `textracted` folder per first-level directory
- 📝 Maintains an up-to-date, auditable catalog for downstream workflows
- 🧩 Modular, standards-driven Python codebase (Hexagonal Architecture)
- ⚡ Fast, idempotent, and CLI-first (no interactive prompts)

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

### Example `folder_paths.json`
```json
{
  "root_folder_path": "/path/to/your/files",
  "catalog_folder": "_catalog",
  "extract_path": "textracted",
  "excluded_files": ["Web-Docs/", "README.md"]
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

- Only one main operation runs per invocation: `--identify`, `--catalog`, `--analysis`, or (default) incremental update.
- Modifier flags (`--convert`, `--tokenize`, `--verbose`) stack and modify the main operation.
- If multiple main-operation flags are passed, the first matched in priority order is executed: `--identify` > `--catalog` > `--analysis` > default.
- Mutually exclusive flags are not enforced by argparse; user should avoid passing conflicting main-operation flags.

#### Scenario Table

| Scenario                         | Catalog Mode      | Extraction/Convert | Tokenize | Verbose | Notes                                 |
|-----------------------------------|-------------------|--------------------|----------|---------|---------------------------------------|
| (1) No flags                     | Incremental       | No                 | No       | No      | Only new files catalogued             |
| (2) --catalog                    | Full rebuild      | No                 | No       | No      | Catalog replaced                      |
| (3) --catalog --convert --tokenize| Full rebuild      | Yes                | Yes      | No      | All features active                   |
| (4) --convert --verbose          | Incremental       | Yes                | No       | Yes     | Extraction + logging, no token count  |

> **Note:** If you pass multiple main-operation flags (e.g., `--catalog --analysis`), only the first in priority order will run. Modifiers can be freely combined with any main operation.

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

| relative_path | filename | extension | textracted |
|---------------|----------|-----------|------------|
| 2024/letters  | file1    | pdf       | True       |
| 2024/images   | img1     | jpg       |            |

- Extracted text: `your_root/2024/textracted/file1.txt`

---

## Troubleshooting
- Make sure all paths in `folder_paths.json` are correct and absolute
- Only PDFs are extracted; other files are just catalogued
- Rerun safely: extraction is idempotent

---

## License

Distributed under the MIT License. See LICENSE for more information.

---
