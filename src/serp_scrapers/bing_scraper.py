import os
import time
import random
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

delay_range = (1, 3)           # min/max delay between requests in seconds
# ———————— #


# A set of domains you know you want to skip
EXCLUDED_DOMAINS = {
    "www.zhihu.com",
    "zhihu.com",
    # add more if you keep seeing other Chinese sites
}

def fetch_bing_results(query, start, batch_size):
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        ]),
        "Accept-Language": "en-PK,en;q=0.9",
    }
    params = {
        "q": query,
        "first": start,
        "count": batch_size,
        "mkt": "en-PK",                           # Pakistan market, English UI
        "cc": "PK",                               # Country code override
        "setLang": "en",                          # Force English pages
        "qft": "+filterui:language-LangEn",       # Bing UI filter for English
        "ensearch": "1",                          # Enhanced search parsing
    }

    resp = requests.get("https://www.bing.com/search",
                        params=params,
                        headers=headers,
                        timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for item in soup.select("li.b_algo"):
        h2 = item.find("h2")
        if not h2 or not h2.a:
            continue
        title = h2.get_text(strip=True)
        link  = h2.a["href"]

        # programmatically skip excluded domains
        domain = urlparse(link).netloc.lower()
        if domain in EXCLUDED_DOMAINS:
            print("Domain Excluded")
            continue

        results.append((title, link))
    return results


def scrape_bing_to_csv(query, output_file, max_results, batch_size):
    # Remove existing file so each run starts fresh
    if os.path.exists(output_file):
        os.remove(output_file)

    total_written = 0
    header_written = False

    for offset in range(1, max_results, batch_size):
        try:
            batch = fetch_bing_results(query, offset, batch_size)
            if not batch:
                print(f"No more results at offset {offset}. Stopping.")
                break

            # Append this batch to CSV
            with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                # write header once
                if not header_written:
                    writer.writerow(["Page Title", "URL"])
                    header_written = True

                for title, link in batch:
                    total_written += 1
                    writer.writerow([title, link])

            print(f"Fetched & saved {len(batch)} items from {offset}–{offset+batch_size-1} (total {total_written}).")

        except Exception as e:
            print(f"Error at offset {offset}: {e}. Retrying after delay.")
        time.sleep(random.uniform(*delay_range))

    print(f"\nDone! {total_written} total results saved to {output_file}")

