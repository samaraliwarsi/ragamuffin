import os
import chromadb
import ollama
import frontmatter

# --- CONFIGURATION ---
# POINT THIS TO YOUR OBSIDIAN NOVEL FOLDER
VAULT_PATH = r"D:\Obsidian Vault\Talisman\Kinor" 
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Splits text into chunks of a specific size with overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def build_index():
    print(f"Connecting to ChromaDB at {CHROMA_DB_PATH}...")
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    # Delete existing collection if it exists to start fresh
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    
    print(f"Scanning vault at {VAULT_PATH}...")
    
    doc_id = 0
    for root, _, files in os.walk(VAULT_PATH):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                
                # 1. READ AND STRIP FRONTMATTER
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    clean_text = post.content.strip()
                
                # Skip empty files (like your Longform index files)
                if not clean_text:
                    continue
                    
                print(f"Processing: {file} ({len(clean_text)} chars of prose)")
                
                # 2. CHUNK THE CLEAN PROSE
                chunks = chunk_text(clean_text)
                
                # 3. EMBED AND STORE
                for i, chunk in enumerate(chunks):
                    # Get embedding from Ollama
                    response = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)
                    embedding = response["embedding"]
                    
                    # Add to ChromaDB
                    collection.add(
                        ids=[f"doc_{doc_id}"],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{"source": file, "chunk_index": i}]
                    )
                    doc_id += 1
                    
    print(f"\nSuccess! Indexed {doc_id} chunks into ChromaDB.")

if __name__ == "__main__":
    build_index()