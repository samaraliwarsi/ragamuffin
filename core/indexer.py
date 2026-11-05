import os
import chromadb
import ollama
import frontmatter

VAULT_PATH = r"D:\Path\To\Your\Obsidian\Vault\Kinor" # CHANGE THIS
CHROMA_DB_PATH = "data/chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def build_index():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    
    doc_id = 0
    for root, _, files in os.walk(VAULT_PATH):
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