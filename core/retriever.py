import chromadb
import ollama

CHROMA_DB_PATH = "data/chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "ministral-3:14b"

def get_context(query, n_results=6, anchor_files=None):
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    
    documents = []
    metadata_list = []
    
    # 1. Fetch anchor files first (if any)
    if anchor_files:
        for anchor in anchor_files:
            anchor_results = collection.get(where={"source": anchor})
            if anchor_results["documents"]:
                documents.extend(anchor_results["documents"])
                metadata_list.extend(anchor_results["metadatas"])
                n_results = max(1, n_results - len(anchor_results["documents"]))

    # 2. Vector Search for the rest
    if n_results > 0:
        response = ollama.embeddings(model=EMBED_MODEL, prompt=query)
        results = collection.query(
            query_embeddings=[response["embedding"]],
            n_results=n_results
        )
        documents.extend(results["documents"][0])
        metadata_list.extend(results["metadatas"][0])
    
    context_string = ""
    for doc, meta in zip(documents, metadata_list):
        context_string += f"--- Source: {meta['source']} ---\n{doc}\n\n"
        
    return context_string, metadata_list

def ask_ollama_stream(query, context, history, mode="Strict", keep_alive="5m", system_prompt=""):
    temp = 0.1 if mode == "Strict" else 0.7
    
    if not system_prompt.strip():
        system_prompt = """You are an expert lore keeper and creative writing partner for a novelist. 
        Answer the user's question using ONLY the provided context from their notes. 
        When brainstorming or ideating, separate canon facts from new ideas clearly."""

    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in history:
        messages.append({'role': msg["role"], 'content': msg["content"]})

    user_prompt = f"""Context from the novel's notes:
{context}

User Question: {query}"""

    messages.append({'role': 'user', 'content': user_prompt})

    stream = ollama.chat(
        model=CHAT_MODEL,
        messages=messages,
        options={'temperature': temp, 'num_ctx': 8192},
        keep_alive=keep_alive,
        stream=True
    )

    for chunk in stream:
        yield chunk['message']['content']


def get_all_sources():
    """Returns a sorted list of all unique file names in the ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
        results = collection.get(include=['metadatas'])
        sources = set(meta['source'] for meta in results['metadatas'])
        return sorted(list(sources))
    except Exception:
        return []