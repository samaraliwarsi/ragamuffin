import os
import json
import chromadb
import ollama
import frontmatter
import hashlib

CHROMA_DB_PATH = "data/chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
SYNC_STATE_FILE = "data/sync_state.json"

def get_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def build_index(vault_path):
    if not vault_path or not os.path.exists(vault_path):
        print(f"Error: Vault path '{vault_path}' is invalid.")
        return 0

    # Load previous sync state
    sync_state = {}
    if os.path.exists(SYNC_STATE_FILE):
        with open(SYNC_STATE_FILE, 'r') as f:
            sync_state = json.load(f)

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # IMPORTANT: Use get_or_create, NOT delete_collection!
    collection = client.get_or_create_collection(COLLECTION_NAME)
    
    processed_count = 0
    current_files = set()

    # 1. Add or Update changed files
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                current_files.add(file)
                filepath = os.path.join(root, file)
                file_hash = get_file_hash(filepath)
                
                # Check if file has changed
                if sync_state.get(file) == file_hash:
                    continue # Skip unchanged file
                    
                print(f"Processing: {file}")
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    clean_text = post.content.strip()
                
                # Remove old chunks for this file
                try:
                    collection.delete(where={"source": file})
                except Exception:
                    pass

                if not clean_text:
                    sync_state[file] = file_hash
                    continue
                    
                chunks = chunk_text(clean_text)
                for i, chunk in enumerate(chunks):
                    response = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)
                    collection.add(
                        ids=[f"doc_{file}_{i}"], # Use file name in ID to avoid collisions
                        embeddings=[response["embedding"]],
                        documents=[chunk],
                        metadatas=[{"source": file, "chunk_index": i}]
                    )
                
                processed_count += 1
                sync_state[file] = file_hash

    # 2. Remove deleted files from DB
    for old_file in list(sync_state.keys()):
        if old_file not in current_files:
            print(f"Removing deleted file: {old_file}")
            try:
                collection.delete(where={"source": old_file})
            except Exception:
                pass
            del sync_state[old_file]

    # Save updated state
    os.makedirs("data", exist_ok=True)
    with open(SYNC_STATE_FILE, 'w') as f:
        json.dump(sync_state, f, indent=4)
        
    return processed_count