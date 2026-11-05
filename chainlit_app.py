import chainlit as cl
import chromadb
import ollama

# --- CONFIGURATION ---
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "novel_lore"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "ministral-3:14b"

# --- RAG FUNCTIONS ---
def get_context(query, n_results):
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)
    
    response = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    results = collection.query(
        query_embeddings=[response["embedding"]],
        n_results=n_results
    )
    
    documents = results["documents"][0]
    metadata = results["metadatas"][0]
    
    context_string = ""
    for doc, meta in zip(documents, metadata):
        context_string += f"--- Source: {meta['source']} ---\n{doc}\n\n"
        
    return context_string, metadata

def ask_ollama(query, context, temp=0.3):
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

# --- CHAINLIT UI LIFECYCLE ---

@cl.on_chat_start
async def start():
    await cl.Message(content="Ragamuffin is ready. Ask about your novel.").send()

@cl.on_message
async def main(message: cl.Message):
    # 1. Create a blank message that shows a loading spinner
    msg = cl.Message(content="Searching the vault...")
    await msg.send()
    
    try:
        # 2. Get context and generate answer
        context, metadata = get_context(message.content, n_results=6)
        
        msg.content = "Writing..."
        await msg.update()
        
        answer = ask_ollama(message.content, context, temp=0.3)
        
        # 3. Update the message with the final answer
        msg.content = answer
        await msg.update()
        
        # 4. Send the sources as a separate message
        sources_text = "**📖 Sources Used:**\n"
        for src in sorted(set(m['source'] for m in metadata)):
            sources_text += f"- {src}\n"
        await cl.Message(content=sources_text).send()
        
    except Exception as e:
        msg.content = f"An error occurred: {str(e)}"
        await msg.update()