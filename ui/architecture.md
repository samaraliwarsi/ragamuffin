# Architecture & Agent Guidelines

This document outlines the structure, tech stack, and critical workarounds for RAGamuffin.
## Directory Structure
```text
RAGamuffin/
├── app.py                 # Main entry point (Python backend, UI event loop, threading)
├── config.json            # User settings (auto-generated)
├── chat_history.json      # Persistent chat log (auto-generated)
├── data/
│   ├── chroma_db/         # ChromaDB vector storage
│   └── sync_state.json    # MD5 hashes of synced files for incremental updates
├── core/
│   ├── indexer.py         # Vault scanning, frontmatter stripping, chunking, embedding
│   └── retriever.py       # ChromaDB querying, context assembly, Ollama API wrapper
├── ui/
│   ├── main-window.slint  # Main layout (sidebar, chat area, input)
│   ├── chat-message.slint # Individual chat bubbles
│   └── settings-panel.slint # Settings modal
└── streamlit_backup/      # Fallback Streamlit UI (shares the same core/ and data/)
```

## 🚨 Critical Framework Quirks & Workarounds

If you are an AI agent working on this repo, **READ THIS FIRST** to avoid repeating past mistakes.

### 1. Slint Thread Safety (The Panic)
- **Rule:** NEVER update a Slint property (`self.messages`, `self.notification`) from a background thread (`threading.Thread`). Slint's Rust backend will panic (`ComponentInstance is unsendable`).
- **Workaround:** Background threads must push data to a `queue.Queue`. A `slint.Timer` running on the main thread polls this queue every 100ms and updates the UI safely.

### 2. Slint Markdown Rendering (The StyledText Workaround)
- **The Problem:** Slint's Python bindings (v1.18.1b1) do not support real-time rendering of dynamic Markdown strings via the standard `Text` element. Furthermore, the built-in `StyledText` element has a bug where it fails to update dynamically during streaming.
- **The Solution:** We bypass the real-time bug by parsing the Markdown on the Python side. 
  - The LLM streams raw Markdown.
  - In `app.py`, the `_parse_markdown()` helper uses `slint.StyledText.from_markdown()` to convert the string into a native Slint object.
  - This object is passed to the UI via the `formatted_message` property.
  - The UI uses a `StyledText` element in `chat-message.slint` to render the parsed object.
- **Data Model Split:** Every message maintains two fields:
  1. `content`: The raw Markdown string (used for saving to `chat_history.json` and the "Copy" button).
  2. `formatted_message`: The `StyledText` object (used exclusively for UI rendering).
- **Future Work:** If Slint officially fixes dynamic `Text` rendering or real-time `StyledText` streaming, we can easily revert by binding the UI to `content` and deleting the `_parse_markdown` function. The raw data is already perfectly preserved.

### 3. Slint Layout Quirks
- **`else` is invalid:** You cannot use `} else : Element {` in Slint. You must use two separate `if` statements (e.g., `if (is-editing) : A` and `if (!is-editing) : B`).
- **Vertical Centering:** `alignment: center` on a `HorizontalBox` centers items *horizontally*. To center items vertically, use `HorizontalLayout` with `cross-axis-alignment: center;`.
- **Shrinking Boxes:** Chat bubbles must have `height: self.preferred-height;` to prevent them from collapsing or shrinking after render.

### 4. Windows Resize Artifact
- **Rule:** The `winit` backend on Windows causes a white/black flicker during window resizing. This is a known DWM interaction bug.
- **Workaround:** No Python-level fix exists. `SLINT_BACKEND="winit-femtovg"` is the most stable, but the artifact will still occur. Do not waste time trying to fix it via code.

### 5. Slint ListModel Chameleon
- **Rule:** When reading from a `slint.ListModel`, items might be returned as Python dicts OR Slint structs.
- **Workaround:** Always use helper functions like `get_messages_as_dicts()` that check `hasattr(m, "role")` before attempting dictionary access (`m["role"]`).

### 6. Slint Data Models (Structs & Properties)
To pass complex data from Python to the UI, the `.slint` files define structs. Python dictionaries passed into a `slint.ListModel` **must** exactly match these keys.

**In `ui/main-window.slint`:**
```slint
export struct MessageData {
    role: string,
    content: string,               // Raw Markdown (for JSON/Copy)
    sources: string,               // Comma-separated filenames
    formatted-message: styled-text // The parsed Markdown object
}

export struct AnchorFile {
    name: string,
    selected: bool,
}
```

- **Kebab-case vs Snake_case:** Slint uses kebab-case (`formatted-message`). When accessed from Python, Slint automatically maps this to snake_case (`formatted_message`). 
- **The `StyledText` Property:** Note that `formatted-message` cannot be initialized with a string in Python; it *must* be initialized using `slint.StyledText.from_markdown()` or `slint.StyledText.from_plain_text()`.

## Threading Model
1. User types a message and hits Send.
2. `app.py` appends the user message and triggers `run_query` in a `threading.Thread`.
3. `run_query` calls `get_context` (ChromaDB) and `ask_ollama_stream` (Ollama).
4. As chunks arrive, they are pushed to `self.ui_queue` as `("stream_chunk", text)`.
5. The main thread's `process_ui_queue` timer catches the chunk, appends it to the active chat bubble, and re-renders.