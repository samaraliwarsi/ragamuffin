import streamlit as st
import json
import os
import sys
import chromadb

# 1. Set the working directory to the ROOT folder
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(ROOT_DIR)

# 2. Tell Python where to find the 'core' module
sys.path.append(ROOT_DIR)
from core.indexer import build_index
from core.retriever import get_context, ask_ollama

# --- CONFIGURATION ---
HISTORY_FILE = os.path.join(ROOT_DIR, "chat_history.json")
CSS_FILE = os.path.join(os.path.dirname(__file__), "streamlint-styles.css")

st.set_page_config(page_title="Ragamuffin (Backup)", page_icon="📚", layout="wide", initial_sidebar_state="expanded")

# Load custom CSS
if os.path.exists(CSS_FILE):
    with open(CSS_FILE) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📚 Ragamuffin: Streamlit Backup")

# --- FETCH AVAILABLE FILES FOR ANCHORING ---
@st.cache_resource
def get_all_sources():
    try:
        client = chromadb.PersistentClient(path="data/chroma_db")
        collection = client.get_collection("novel_lore")
        results = collection.get(include=['metadatas'])
        sources = set(meta['source'] for meta in results['metadatas'])
        return sorted(list(sources))
    except Exception:
        return []

# --- CHAT PERSISTENCE ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    if st.button("🔄 Rebuild Database"):
        with st.spinner("Indexing vault..."):
            count = build_index()
            get_all_sources.clear() # Clear cache so new files show up
            st.success(f"Indexed {count} chunks!")
    
    st.markdown("---")
    
    # THE FILE SELECTOR IS BACK
    available_sources = get_all_sources()
    anchor_files = st.multiselect(
        "Anchor Files (Force read these files):", 
        available_sources,
        help="Select multiple files to force them into the context."
    )
    
    st.markdown("---")
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
    num_chunks = st.slider("Max Context Snippets", 2, 16, 6)
    
    st.markdown("---")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        save_history([])
        st.rerun()

# --- INITIALIZE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = load_history()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- CHAT LOGIC ---
if prompt := st.chat_input("Ask about your novel..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            # Pass the anchor_files to the context function
            context, metadata = get_context(prompt, n_results=num_chunks, anchor_files=anchor_files)
            
        with st.spinner("Writing..."):
            answer = ask_ollama(prompt, context, temp=temperature)
            
        st.markdown(answer)
        
        with st.expander("📖 View Sources"):
            unique_sources = set(m['source'] for m in metadata)
            for src in sorted(unique_sources):
                st.write(f"- {src}")
            
    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_history(st.session_state.messages)