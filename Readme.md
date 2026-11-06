# RAGamuffin

  A local, privacy-first RAG (Retrieval-Augmented Generation) desktop application designed specifically for querying an Obsidian vault. Built for novelists and worldbuilders who want to chat with their notes without sending data to the cloud.

  ## Features

- **True Local Execution:** Uses Ollama for chat generation and embeddings.
- **Frontmatter Stripping:** Automatically ignores YAML metadata so it doesn't pollute vector search.
- **Incremental Sync:** Uses MD5 hashing to only re-index files that have changed.
- **Multi-File Anchoring:** Force specific chapters or character sheets into the context window.
- **VRAM Management:** Hard-capped context windows and Ollama `keep_alive` timers to prevent GPU overflow.
- **Chat Persistence:** Rolling chat history that survives app restarts.
- **Stop Generation:** Instantly halt the AI mid-stream.
- **Native Desktop UI:** Built with Slint for a lightweight, low-RAM footprint. (Note: Renders raw text; Markdown styling is not yet supported by the framework's Python bindings).

## Prerequisites

1. [Ollama](https://ollama.com/) installed and running.
2. Pull the required models:
3. Python 3.12+

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:

    ```bash

    python -m venv venv

    .\venv\Scripts\activate  # Windows

    source venv/bin/activate # Mac/Linux

    ```

3. Install dependencies:

    ```bash

    pip install -r requirements.txt

    ```

## Usage

1. Ensure the Ollama background service is running.
2. Launch the app:

    ```bash

    python app.py

    ```

3. Open Settings, set your Vault path, and Sync Vault to Database.
4. Start chatting.
## Backup UI
A Streamlit-based fallback UI is located in the streamlit_backup/ folder. Launch it via:

```bash

streamlit run streamlit_backup/streamlit_app.py

```