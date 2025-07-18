import os
import time
import csv
import requests
from dotenv import load_dotenv

# —— Configuration —— #
ENDPOINT    = "https://google.serper.dev/search"
delay_range = (1, 2)              # polite delay between requests (s)

load_dotenv() # take environment variables from .env.
# ———————— #

def fetch_serper_page(query, page, page_size):
    """
    Fetch one 'page' of results from Serper.dev.
    Returns list of (title, link) tuples from the 'organic' field.
    """
    headers = {
        "X-API-KEY": os.getenv("API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "page": page,
        "num": page_size
    }
    resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    items = []
    for entry in data.get("organic", []):
        title = entry.get("title")
        link  = entry.get("link")
        if title and link:
            items.append((title, link))
    return items

def scrape_google_to_csv(query, max_results, page_size, output_file):
    # fresh CSV
    if os.path.exists(output_file):
        os.remove(output_file)

    total_written = 0
    header_written = False
    pages_needed = (max_results + page_size - 1) // page_size

    for page in range(1, pages_needed + 1):
        try:
            batch = fetch_serper_page(query, page, page_size)
            if not batch:
                print(f"No results returned on page {page}. Stopping.")
                break

            with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                if not header_written:
                    writer.writerow(["Page Title", "URL"])
                    header_written = True

                for title, link in batch:
                    total_written += 1
                    writer.writerow([title, link])

            start_idx = (page - 1) * page_size + 1
            end_idx   = start_idx + len(batch) - 1
            print(f"Page {page}: saved {len(batch)} items ({start_idx}–{end_idx}, total {total_written}).")

            if total_written >= max_results:
                print("Reached max_results limit.")
                break

        except Exception as e:
            print(f"Error on page {page}: {e}. Retrying after delay.")
        time.sleep(__import__("random").uniform(*delay_range))

    print(f"\nDone! {total_written} total results saved to {output_file}")

