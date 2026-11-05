import chromadb
import ollama

# --- CONFIGURATION ---
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "ministral-3:14b"
NUM_CHUNKS = 6  # How many snippets to retrieve

def get_context(query):
    """Embeds the question, searches ChromaDB, and returns the top chunks."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    
    # 1. Embed the user's question
    response = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    query_embedding = response["embedding"]
    
    # 2. Search the database
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=NUM_CHUNKS
    )
    
    # 3. Format the results
    documents = results["documents"][0]
    metadata = results["metadatas"][0]
    
    context_string = ""
    print("\n--- Sources Retrieved ---")
    for i, (doc, meta) in enumerate(zip(documents, metadata)):
        print(f"{i+1}. {meta['source']}")
        context_string += f"--- Source: {meta['source']} ---\n{doc}\n\n"
    print("-------------------------\n")
    
    return context_string

def ask_ollama(query, context):
    """Sends the prompt and context to the local LLM."""
    
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
        options={
            'temperature': 0.3,  # Low temp for factual accuracy
            'num_ctx': 8192      # Strict context window limit
        }
    )
    
    return response['message']['content']

if __name__ == "__main__":
    print("Welcome to Ragamuffin! Type 'quit' to exit.")
    while True:
        user_input = input("\nAsk a question: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        print("Searching database...")
        context = get_context(user_input)
        
        print("Generating answer...")
        answer = ask_ollama(user_input, context)
        
        print(f"\nAI: {answer}\n")