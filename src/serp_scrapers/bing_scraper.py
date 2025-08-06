import os
import time
import random
import csv
import sys
import urllib.parse
import http.client
from urllib.parse import urlparse
from oxylabs import RealtimeClient
from bs4 import BeautifulSoup

# ————— Configuration ————— #
delay_range = (1, 2)           # min/max delay between requests in seconds

# A set of domains you know you want to skip
EXCLUDED_DOMAINS = {
    "www.zhihu.com",
    "zhihu.com",
    # add more if needed
}

# # Oxylabs credentials (set these in your environment)
# OXY_USERNAME = os.getenv("OXY_USERNAME")
# OXY_PASSWORD = os.getenv("OXY_PASSWORD")

# WebScrapingAPI credentials (you can also set this in your env)
WSA_API_KEY = os.getenv("WSA_API_KEY")
WSA_HOST    = "api.webscrapingapi.com"


EAST_COAST_ZIPCODES = [
    # Maine
    "04032",  # Westbrook, ME
    "04101",  # Portland, ME
    "04401",  # Bangor, ME

    # New Hampshire
    "03101",  # Manchester, NH
    "03801",  # Portsmouth, NH

    # Massachusetts
    "02108",  # Boston, MA
    "02139",  # Cambridge, MA
    "02215",  # Boston (Fenway), MA
    "01002",  # Amherst, MA
    "02703",  # Fall River, MA

    # Rhode Island
    "02903",  # Providence, RI
    "02840",  # East Providence, RI

    # Connecticut
    "06103",  # Hartford, CT
    "06810",  # Greenwich, CT
    "06510",  # New Haven, CT

    # New York
    "10001",  # New York, NY
    "11201",  # Brooklyn, NY
    "10451",  # Bronx, NY
    "12207",  # Albany, NY
    "14604",  # Rochester, NY

    # New Jersey
    "07102",  # Newark, NJ
    "08002",  # Cherry Hill, NJ
    "08701",  # Toms River, NJ
    "07030",  # Hoboken, NJ

    # Pennsylvania
    "19101",  # Philadelphia, PA
    "15213",  # Pittsburgh, PA
    "17101",  # Harrisburg, PA
    "16801",  # State College, PA

    # Delaware
    "19901",  # Dover, DE
    "19711",  # Wilmington, DE

    # Maryland
    "21201",  # Baltimore, MD
    "20740",  # Laurel, MD
    "21401",  # Annapolis, MD

    # Virginia
    "22301",  # Alexandria, VA
    "23219",  # Richmond, VA
    "24060",  # Blacksburg, VA

    # North Carolina
    "27514",  # Chapel Hill, NC
    "27601",  # Raleigh, NC
    "28202",  # Charlotte, NC

    # South Carolina
    "29201",  # Columbia, SC
    "29601",  # Greenville, SC
    "29401",  # Charleston, SC

    # Georgia
    "30303",  # Atlanta, GA
    "31401",  # Savannah, GA
    "31501",  # Brunswick, GA

    # Florida
    "33101",  # Miami, FL
    "32801",  # Orlando, FL
    "32301",  # Tallahassee, FL
    "32202",  # Jacksonville, FL
    "32114",  # Daytona Beach, FL
]

# # Initialize a single RealtimeClient for all requests
# client = RealtimeClient(OXY_USERNAME, OXY_PASSWORD)
# # —————————————————————— #

# def fetch_bing_results(query, start, batch_size):
#     """
#     Fetch one page of Bing results via Oxylabs Realtime API.
#     On 403 (credits exhausted), exit the whole program.
#     """
#     # Pick a random East-Coast ZIP code each time
#     geo = random.choice(EAST_COAST_ZIPCODES)

#     # Oxylabs pages are 1-based
#     page_num = (start - 1) // batch_size + 1

#     try:
#         resp = client.bing.scrape_search(
#             query,
#             start_page=page_num,
#             pages=1,
#             limit=batch_size,
#             parse=True,
#             geo_location=geo
#         )
#     except Exception as e:
#         # try to detect a 403 from the SDK exception
#         code = getattr(e, "status_code", None)
#         if code == 403 or "403" in str(e):
#             print("ERROR: Oxylabs free-trial credits exhausted (HTTP 403).")
#             sys.exit(1)
#         # otherwise, re-raise so outer loop can retry/log
#         raise

#     results = []
#     for page in resp.results:
#         organic = page.content.get("results", {}).get("organic", [])
#         for item in organic:
#             title = item.get("title")
#             link  = item.get("link") or item.get("url")
#             if not title or not link:
#                 continue

#             # domain exclusion logic
#             domain = urlparse(link).netloc.lower()
#             if domain in EXCLUDED_DOMAINS:
#                 print(f"Domain Excluded: {domain}")
#                 continue

#             results.append((title, link))

#     return results

def fetch_bing_results(query, start, batch_size):
    """
    Fetch one page of Bing results via WebScrapingAPI.
    Returns up to batch_size (title, link) tuples, skipping excluded domains.
    """
    # build the actual Bing URL you want proxied
    bing_url = (
        "https://www.bing.com/search?"
        + urllib.parse.urlencode({
            "q": query,
            "count": batch_size,
            "offset": start-1,    # Bing’s “first” param is 1-based index
        })
    )

    # make the proxied request
    conn = http.client.HTTPSConnection(WSA_HOST)
    params = urllib.parse.urlencode({
        "api_key": WSA_API_KEY,
        "url": bing_url,
        "country": "us",
    })
    conn.request("GET", f"/v2?{params}")
    resp = conn.getresponse()

    # if resp.status != 200:
    #     print(f"Error fetching from WebScrapingAPI: HTTP {resp.status}")
    #     sys.exit(1)

    html = resp.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    # Bing’s organic results are in <li class="b_algo">
    for li in soup.select("li.b_algo")[:batch_size]:
        h2 = li.find("h2")
        if not h2 or not h2.a:
            continue
        title = h2.get_text(strip=True)
        link  = h2.a["href"]

        # domain exclusion
        domain = urlparse(link).netloc.lower()
        if domain in EXCLUDED_DOMAINS:
            print(f"Domain Excluded: {domain}")
            continue

        results.append((title, link))

    # be a good citizen
    # time.sleep(random.uniform(*delay_range))
    return results

def scrape_bing_to_csv(query, output_file, max_results, batch_size):
    # Remove existing file so each run starts fresh
    if os.path.exists(output_file):
        os.remove(output_file)

    ## OVERRIDE USER
    # batch_size=20

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
