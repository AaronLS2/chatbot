from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import chromadb
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load OpenAI API Key
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI
app = FastAPI()

# Connect to ChromaDB
chroma_client = chromadb.PersistentClient(path="./chromadb")
collection = chroma_client.get_collection("studentaid")

# ✅ Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)

# ✅ In-memory session storage for multi-turn memory
session_memory = {}

# ✅ Define request model
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

# Validate API key  
async def verify_api_key(api_key: str = Header(...)):  
    if api_key != os.getenv("API_KEY"):  
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/chat")
def chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """
    Chatbot API with multi-turn memory.
    Accepts JSON input and returns structured JSON responses.
    """

    try:
        q = request.query
        session_id = request.session_id

        logging.debug(f"🔹 Received query: {q}")

        # Retrieve or initialize session history
        if session_id not in session_memory:
            session_memory[session_id] = []

        history = session_memory[session_id]

        # Convert user question into an embedding
        query_embedding = openai_client.embeddings.create(input=[q], model="text-embedding-ada-002").data[0].embedding

        # Search for the best-matching content
        results = collection.query(query_embeddings=[query_embedding], n_results=3)

        logging.debug(f"🔹 ChromaDB Results: {results}")

        if "metadatas" in results and results["metadatas"] and results["metadatas"][0]:
            # ✅ Pick the best match based on similarity
            best_match_index = results["distances"][0].index(min(results["distances"][0]))
            best_metadata = results["metadatas"][0][best_match_index]

            raw_text = best_metadata.get("content", "No relevant content found.")
            source_url = best_metadata.get("url", "No source available")

            # ✅ Debugging before calling OpenAI
            logging.debug(f"🔹 Using this data for OpenAI: {raw_text[:200]}...")  # Print first 200 chars

            # ✅ Build a conversation-aware prompt
            chat_history = "\n".join([f"User: {msg['user']}\nBot: {msg['bot']}" for msg in history])
            prompt = f"""
            You are a friendly chatbot helping users with FAFSA and student aid.
            Keep responses concise, engaging, and helpful.

            Previous conversation:
            {chat_history}

            The user just asked: "{q}"
            Here is relevant information from a trusted source:
            {raw_text}

            Respond in a **friendly, natural way** and include the source link: {source_url}
            """

            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )

            conversational_response = response.choices[0].message.content.strip()

            # ✅ Store message in session memory
            history.append({"user": q, "bot": conversational_response})
            session_memory[session_id] = history

            # ✅ Return structured JSON response
            return JSONResponse(
                content={
                    "response": conversational_response,
                    "source": source_url,
                    "history": history  # ✅ Send history back for debugging
                },
                status_code=200
            )

        return JSONResponse(
            content={"response": "I couldn't find anything on that topic.", "source": None},
            status_code=200
        )

    except Exception as e:
        logging.error(f"❌ FastAPI encountered an error: {e}", exc_info=True)
        return JSONResponse(
            content={"response": "Sorry, I ran into an issue. Please try again later.", "source": None},
            status_code=500
        )

# ✅ Run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
