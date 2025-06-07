# Library Manager Lite

Effortlessly manage, search, and analyze thousands of research documents—PDFs, images, text files, and more—with agentic automation and analytics.

---

## Key Features

### 1. Scalable Library Catalog
- Manage 1,000s of documents (PDFs, images, txt, etc.)
- Unified catalog in both CSV and SQLite formats
- Rich analytics: file metadata, usage stats, and more
- Add YouTube transcripts directly to your library (subtitles converted to TXT in desired folder)
- Automatically convert PDFs to TXT, MD files to TXT, and VTT files to TXT

### 2. Agentic PDF Renaming
- Automatically rename PDFs in your download folder
- Best-guess extraction for `Author - Title (Year)`
- Ensures clean, research-ready filenames before adding to your library
- LiteLLM abstraction allows you to pick your preferred models and provide your own API keys

### 3. Multi-Library Profiles & Default Selection
- Seamlessly manage multiple libraries using profiles
- Instantly switch libraries for different projects or contexts
- Set your default library via a `.env` file

### 4. Simple SQLite Search
- Directly search your library using SQL queries
- Fast, scriptable, and ideal for power users

### 5. Agentic Research Recommendations
- Get smart, AI-driven suggestions for files relevant to your research
- Surface hidden gems and key documents
- LiteLLM abstraction allows you to pick your preferred models and provide your own API keys

### 6. Duplicate Detection
- Find exact duplicates using SHA-256 hashing
- Catch near-duplicates with fuzzy Levenshtein distance matching

---

## Installation

```bash
pip install -r requirements.txt
```
- Python 3.8+
- All dependencies are pinned in `requirements.txt`

---

## Quickstart

1. **Set up your library:**
   - Edit your `.env` file to set `DEFAULT_PROFILE=your_profile_name`
   - Define multiple profiles for different libraries in your config

2. **Scan and catalog your documents:**
   ```bash
   python catalog.py --profile research
   ```

3. **Auto-rename PDFs in your downloads folder:**
   ```bash
   python catalog.py --identify --profile default
   ```

4. **Search your library with multiple keywords:**
   ```bash
   python catalog.py --search
   ```

5. **Get agentic recommendations:**
   ```bash
   python recommend.py --profile sandbox
   ```

6. **Find duplicates:**
   ```bash
   python catalog.py --find-duplicates --profile sandbox
   ```


### CLI Flags

| Flag         | Script(s)                | Description                                                                                 |
|--------------|--------------------------|---------------------------------------------------------------------------------------------|
| --search     | catalog.py               | Search filenames in the SQLite database; supports multi-term queries (semicolon-separated). Only searches .txt files. |
| --recatalog  | catalog.py               | Full catalog rebuild (includes text conversion and tokenization)                            |
| --analysis   | catalog.py               | Output summary analysis to latest-breakdown.txt                                             |
| --verbose    | catalog.py               | Log every process iteration                                                                 |
| --tokenize   | catalog.py               | Count tokens in TXT files and add to catalog                                                |
| --convert    | catalog.py               | Convert PDFs to TXT, MD files to TXT, and VTT files to TXT                                  |
| --identify   | catalog.py               | Rename PDFs in buffer_folder using LLM                                                      |
| --transcribe | catalog.py               | Download YouTube transcripts, convert VTT to TXT, update catalog                            |
| --backupdb   | catalog.py               | Create timestamped backup of the SQLite database                                            |
| --profile    | catalog.py, recommend.py | Profile performance of scripts                                                              |

## Configuration

- **`.env` file:**
  - Set `DEFAULT_PROFILE=your_profile_name`
  - Other options: library root path, analytics settings
- **Profiles:**
  - Define multiple profiles in your config to manage different libraries
  - Switch profiles using the `--profile` flag or by changing `.env`

---

## Catalog & Analytics

- Catalog is stored as both CSV and SQLite for flexibility
- Tracks metadata: relative path, filename, extension, last modified, file size, text extraction status, token count
- Analytics tools help you understand your library's composition and usage

---

## License

MIT License. See `LICENSE` for details.
