import requests
import psycopg2  # PostgreSQL library
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re

# Database connection
DB_PARAMS = {
    "dbname": "chatbot_data",
    "user": "als",  # Your PostgreSQL username
    "password": "postgrespw",  # Your PostgreSQL password
    "host": "localhost",
    "port": "5432",
}

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_PARAMS)
cur = conn.cursor()

# Create table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS scraped_pages (
        id SERIAL PRIMARY KEY,
        url TEXT UNIQUE NOT NULL,
        content TEXT NOT NULL
    );
""")
conn.commit()

# Directories to exclude
EXCLUDED_DIRECTORIES = ["/data-center", "/es/", "/payment", "/dashboard", "/settings", "/feedback-center", "/2425/", "/preview"]

# Function to extract URLs from the local sitemap while filtering out unwanted ones
def get_sitemap_urls(local_sitemap_file):
    with open(local_sitemap_file, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file.read(), "xml")
    urls = [loc.text for loc in soup.find_all("loc")]

    # Filter out excluded directories
    filtered_urls = [url for url in urls if not any(excluded in url for excluded in EXCLUDED_DIRECTORIES)]
    
    print(f"Filtered URLs: {len(filtered_urls)} out of {len(urls)} total URLs.")
    return filtered_urls

# Set up Selenium with headless Chrome
options = Options()
options.headless = True  # Runs Chrome in headless mode

# Initialize WebDriver with error handling
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(15)  # 15-second timeout to load each page

# Use the local sitemap instead of downloading it
sitemap_file = "sitemap.xml"
urls = get_sitemap_urls(sitemap_file)  # Now scraping all pages

# Loop through URLs and scrape content
for url in urls:
    attempt = 0
    while attempt < 3:  # Retry up to 3 times for each page
        try:
            driver.get(url)
            time.sleep(5)  # Allow JavaScript to load

            # Extract page source after JS execution
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()

            # Get all text
            text = soup.get_text(separator=" ", strip=True)

            # Normalize spaces and make lowercase for reliable searching
            normalized_text = re.sub(r"\s+", " ", text).strip().lower()

            # Find the first major section heading (adjustable: 'h2', 'h3')
            first_heading = soup.find(["h2", "h3"])
            if first_heading:
                heading_text = first_heading.get_text(strip=True)
                # Keep only content after this heading
                text = text.split(heading_text, 1)[-1].strip()

            # Stop extracting content at "Additional Links"
            stop_marker = "additional links"
            match = re.search(rf"{stop_marker}", normalized_text, re.IGNORECASE)
            if match:
                text = text[:match.start()].strip()

            # Remove everything after "Aidan" appears
            aidan_marker = "aidan"
            match_aidan = re.search(rf"{aidan_marker}", normalized_text, re.IGNORECASE)
            if match_aidan:
                text = text[:match_aidan.start()].strip()

            # Insert into PostgreSQL
            cur.execute("INSERT INTO scraped_pages (url, content) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING;", (url, text))
            conn.commit()

            print(f"Scraped & stored: {url}")
            break  # Exit retry loop if successful

        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {url}: {e}")
            time.sleep(5)  # Wait before retrying
            attempt += 1

    if attempt == 3:
        print(f"Skipping {url} after multiple failures.")

# Close browser and database connection
driver.quit()
cur.close()
conn.close()

print("Scraping complete. Data stored in PostgreSQL.")
