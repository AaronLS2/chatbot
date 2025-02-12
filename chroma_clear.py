import chromadb

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chromadb")
collection = chroma_client.get_or_create_collection("studentaid")

# ✅ Fetch all stored document metadata to extract IDs
try:
    stored_data = collection.get(include=["metadatas"])  # Retrieve metadata
    stored_ids = stored_data.get("ids", [])

    if stored_ids:
        collection.delete(ids=stored_ids)  # ✅ Delete by ID
        print(f"✅ Deleted {len(stored_ids)} embeddings from ChromaDB.")
    else:
        print("✅ No embeddings found in ChromaDB.")

except Exception as e:
    print(f"⚠️ Error while deleting ChromaDB embeddings: {e}")

# ✅ Confirm deletion
count = collection.count()
print(f"🔍 ChromaDB now contains {count} documents.")  # Should print 0 if cleared successfully
