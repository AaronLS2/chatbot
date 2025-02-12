import psycopg2
import tiktoken

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

# Load OpenAI's tokenizer
tokenizer = tiktoken.get_encoding("cl100k_base")  # Supports text-embedding-ada-002

# Fetch all scraped pages
cur.execute("SELECT url, content FROM scraped_pages;")
pages = cur.fetchall()

# Analyze token counts
long_pages = []
for url, text in pages:
    token_count = len(tokenizer.encode(text))
    
    if token_count > 8192:
        long_pages.append((url, token_count))  # Track pages that exceed the limit

    print(f"🔹 {url} → {token_count} tokens")

# Print summary of long pages
if long_pages:
    print("\n🚨 Pages exceeding 8192 tokens:")
    for url, count in sorted(long_pages, key=lambda x: x[1], reverse=True):
        print(f"❌ {url} → {count} tokens")

print("\n✅ Token analysis complete!")
