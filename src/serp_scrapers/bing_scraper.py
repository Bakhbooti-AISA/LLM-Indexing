import os
import time
import random
import csv
import requests
from bs4 import BeautifulSoup

delay_range = (1, 3)           # min/max delay between requests in seconds
# ———————— #

def fetch_bing_results(query, start, batch_size):
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            # add more UAs if you like
        ])
    }
    params = {
        "q": query,
        "first": start,        # 1-based index of first result
        "count": batch_size    # number of results to return (max 50)
    }
    resp = requests.get("https://www.bing.com/search", params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for item in soup.select("li.b_algo"):
        title = item.h2.get_text(strip=True) if item.h2 else None
        link  = item.h2.a["href"] if item.h2 and item.h2.a else None
        if title and link:
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

