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

def ask_ollama(query, context, temp=0.3, keep_alive="5m"):
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
        options={'temperature': temp, 'num_ctx': 8192},
        keep_alive=keep_alive
    )
    return response['message']['content']