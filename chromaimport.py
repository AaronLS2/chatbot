import os
import psycopg2
import chromadb
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv

# Load OpenAI API Key
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Connect to PostgreSQL
DB_PARAMS = {
    "dbname": "chatbot_data",
    "user": "als",
    "password": "postgrespw",
    "host": "localhost",
    "port": "5432",
}

conn = psycopg2.connect(**DB_PARAMS)
cur = conn.cursor()

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chromadb")
collection = chroma_client.get_or_create_collection("studentaid")

# Load OpenAI's tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")

# Fetch scraped pages
cur.execute("SELECT url, content FROM scraped_pages;")
pages = cur.fetchall()

# Define max chunk size
MAX_TOKENS_PER_CHUNK = 7000

# Store embeddings with chunking
for url, text in pages:
    tokens = tokenizer.encode(text)

    # If content is small enough, store normally
    if len(tokens) <= MAX_TOKENS_PER_CHUNK:
        embedding_response = openai_client.embeddings.create(input=[text], model="text-embedding-ada-002")
        embedding = embedding_response.data[0].embedding

        collection.add(ids=[url], embeddings=[embedding], metadatas=[{"url": url, "content": text}])
        print(f"✅ Stored: {url} ({len(tokens)} tokens)")

    # If content is too large, split into chunks
    else:
        chunks = [tokens[i:i + MAX_TOKENS_PER_CHUNK] for i in range(0, len(tokens), MAX_TOKENS_PER_CHUNK)]

        for i, chunk in enumerate(chunks):
            chunk_text = tokenizer.decode(chunk)
            embedding_response = openai_client.embeddings.create(input=[chunk_text], model="text-embedding-ada-002")
            embedding = embedding_response.data[0].embedding

            collection.add(
                ids=[f"{url}-part-{i}"], 
                embeddings=[embedding], 
                metadatas=[{"url": url, "content": chunk_text}]
            )
        
        print(f"✅ Chunked & stored: {url} ({len(tokens)} tokens, split into {len(chunks)} parts)")

count = collection.count()
print(f"🔍 ChromaDB now contains {count} documents.")