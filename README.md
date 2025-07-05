# 📚 CBSE Question Parser

## 📁 Project Structure

```
CBSE/
├── 📱 app.py                    # Main application
├── 🔧 config.py                 # Configuration settings
├── 🛠️ utils.py                  # Utility functions
├── 📂 api/                      # API endpoints and routes
├── 🧠 logic/                    # Business logic and processing
├── 📄 pages/                    # UI pages and components
├── 📝 logs/                     # Application logs
├── ⚙️ .streamlit/
│   └── config.toml              # Streamlit auto-config
├── 📦 requirements.txt          # Dependencies
├── 📖 README.md                 # This file
├── 🌍 venv/                     # Virtual environment
└── 🏭 prd/                      # Product Requirement Docs
```

## 📂 Directory Structure Explanation

### Core Application Files

- **`app.py`** - Main Streamlit application entry point
- **`config.py`** - Centralized configuration settings
- **`utils.py`** - Common utility functions

### Feature Directories

- **`api/`** - Here all the api calls to the Gemini's LLM and Amazon Textract will be done

- **`logic/`** - Core business logic, data processing, and algorithm implementations

- **`views/`** - Streamlit Different Page views

- **`logs/`** - Application logs, error logs, and debug information

### Configuration & Dependencies

- **`.streamlit/`** - Streamlit-specific configuration files
- **`requirements.txt`** - Python package dependencies
- **`venv/`** - Virtual environment (not tracked in version control)
- **`prd/`** - Product requirements, documentation, and specifications
