# Directory Structure

This document outlines where to place each component of the application to keep utilities, logging, UI, and business logic fully separated for easy copying and pasting.

## app.py

- Location: `/CBSE/app.py`
- Role: Orchestrator
  - Loads configuration
  - Initializes logging
  - Calls the UI module in `views/` and the business logic in `logic/`

## utils.py

- Location: `/CBSE/utils.py`
- Role: Utility functions
  - Streamlit setup (`setup_page_config`)
  - Filename and folder name generation
  - Any other general-purpose helpers

## logs/logger.py

- Location: `/CBSE/logs/logger.py`
- Role: Logging functions only
  - `init_job_logging(job_name)`: create a unique sub-folder under `logs/pages/`
  - `log_page(page_path)`: record each saved page
  - Any other logging-related utilities
- Usage: import in logic modules:
  ```python
  from logs.logger import init_job_logging, log_page
  ```

## logic/

- Location: `/CBSE/logic/`
- Role: Business logic for PDF processing
  - Splitting multi-page PDFs into single-page PDFs using PyMuPDF
  - Saving pages by calling helpers in `utils.py`
  - Calling logging functions from `logs/logger.py`
  - Should contain no UI or Streamlit code

## views/

- Location: `/CBSE/views/`
- Role: Streamlit UI components only
  - File uploader labeled 'Upload Questions PDF'
  - Display processing status messages and success message
  - No business logic or logging code here
  - Import and call rendering functions or components as needed

## Folder/File Roles at a Glance

- **logs/**: Holds only logging utilities (`logs/logger.py`), responsible for creating unique job sub-folders under `logs/pages/` and recording saved PDF pages.
- **logic/**: Contains business logic for PDF processing (splitting multi-page PDFs into single-page outputs), calls helpers in `utils.py` and logging functions from `logs/logger.py`; no UI or Streamlit code.
- **views/**: All Streamlit UI components live here (file uploader, processing status, success message); no business logic or logging.
- **utils.py**: General-purpose helper functions (Streamlit setup with `setup_page_config`, filename and folder naming, etc.).
- **app.py**: Orchestrator entrypoint—loads configuration, initializes logging, and delegates to `views/` for UI and `logic/` for processing.
- **config.py**: Central place for configuration values (page settings, file paths, etc.).

---

You can now copy and paste any of these modules independently without dragging in unrelated code or clutter.
