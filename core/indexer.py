import os
import json
import chromadb
import ollama
import frontmatter

CHROMA_DB_PATH = "data/chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
CONFIG_FILE = "config.json"

def get_vault_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("vault_path", "")
    return ""

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def build_index():
    vault_path = get_vault_path()
    if not vault_path or not os.path.exists(vault_path):
        print(f"Error: Vault path '{vault_path}' is invalid or missing in config.json.")
        return 0

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    
    doc_id = 0
    for root, _, files in os.walk(vault_path):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    clean_text = post.content.strip()
                
                if not clean_text:
                    continue
                    
                chunks = chunk_text(clean_text)
                for i, chunk in enumerate(chunks):
                    response = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)
                    collection.add(
                        ids=[f"doc_{doc_id}"],
                        embeddings=[response["embedding"]],
                        documents=[chunk],
                        metadatas=[{"source": file, "chunk_index": i}]
                    )
                    doc_id += 1
    return doc_id