import streamlit as st
import chromadb
import ollama
import json
import os
from indexer import build_index

def load_css(file_name):
    with open(file_name, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)



# --- CONFIGURATION ---
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "ministral-3:14b"
HISTORY_FILE = "chat_history.json"

st.set_page_config(page_title="Ragamuffin", page_icon="📚", layout="wide", initial_sidebar_state="expanded")
load_css("styles.css")
st.title("📚 Ragamuffin: Kinor Lore Master")

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

@st.cache_resource
def get_all_sources():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    results = collection.get(include=['metadatas'])
    sources = set(meta['source'] for meta in results['metadatas'])
    return sorted(list(sources))

# --- SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    
    if st.button("🔄 Sync Vault Changes"):
        with st.spinner("Updating database..."):
            build_index() 
            get_all_sources.clear() 
            st.success("Database Synced!")

    st.markdown("---")
    
    available_sources = get_all_sources()
    
    # CHANGED: selectbox to multiselect
    anchor_files = st.multiselect(
        "Anchor Files (Force read these files):", 
        available_sources,
        help="Select multiple files to force them into the context window. Uses more tokens."
    )
    
    temperature = st.slider("Temperature (0.1 = Facts, 0.8 = Creative)", 0.0, 1.0, 0.3, 0.1)
    num_chunks = st.slider("Max Context Snippets", 2, 16, 6, help="Total chunks to send (Anchors + Vector Search)")
    
    st.markdown("---")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        save_chat_history([])
        st.rerun()

# --- INITIALIZE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- RAG FUNCTIONS ---
def get_context(query, n_results, anchor_files):
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    
    # Use dictionaries to deduplicate chunks by ID
    retrieved_docs = {} 
    retrieved_metas = {}
    
    # 1. Fetch ALL chunks from the anchor files
    for anchor in anchor_files:
        anchor_results = collection.get(where={"source": anchor})
        for i, doc_id in enumerate(anchor_results["ids"]):
            retrieved_docs[doc_id] = anchor_results["documents"][i]
            retrieved_metas[doc_id] = anchor_results["metadatas"][i]
            
    anchor_count = len(retrieved_docs)
    
    # 2. Calculate how many slots are left for vector search
    remaining_slots = n_results - anchor_count
    
    if remaining_slots > 0:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=query)
        results = collection.query(
            query_embeddings=[response["embedding"]],
            n_results=remaining_slots
        )
        
        # Add vector search results (deduplicating if they overlap with anchors)
        for i, doc_id in enumerate(results["ids"][0]):
            if doc_id not in retrieved_docs:
                retrieved_docs[doc_id] = results["documents"][0][i]
                retrieved_metas[doc_id] = results["metadatas"][0][i]

    # 3. Format context
    context_string = ""
    final_metas = list(retrieved_metas.values())
    
    for doc_id, doc in retrieved_docs.items():
        meta = retrieved_metas[doc_id]
        context_string += f"--- Source: {meta['source']} ---\n{doc}\n\n"
        
    return context_string, final_metas

def ask_ollama(query, context, temp):
    system_prompt = """You are an expert lore keeper and creative writing partner for a novelist. 
Answer the user's question using ONLY the provided context from their notes. 
If the answer is not in the context, say "I cannot find that in the provided notes."
When brainstorming or ideating, separate canon facts from new ideas clearly."""

    user_prompt = f"""Context from the novel's notes:
{context}

User Question: {query}"""

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        options={'temperature': temp, 'num_ctx': 8192}
    )
    return response['message']['content']

# --- CHAT INPUT ---
if prompt := st.chat_input("Ask about your novel..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Gathering context..."):
            context, metadata = get_context(prompt, num_chunks, anchor_files)
            
        with st.spinner("Writing..."):
            answer = ask_ollama(prompt, context, temperature)
            
        st.markdown(answer)
        
        with st.expander("📖 View Source Chunks Used"):
            unique_sources = set(m['source'] for m in metadata)
            st.write(f"**Total Chunks:** {len(metadata)}")
            for src in sorted(unique_sources):
                st.write(f"- {src}")
            st.markdown("---")
            st.text(context)
            
    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_chat_history(st.session_state.messages)