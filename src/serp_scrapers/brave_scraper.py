from bs4 import BeautifulSoup
import json5
import re
import http
import os
import csv
import time
import random

import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs, unquote, urlunparse, urlencode

# ————— Configuration ————— #
delay_range = (1, 2)           # min/max delay between requests in seconds

# A set of domains you know you want to skip
EXCLUDED_DOMAINS = {
    "www.zhihu.com",
    "zhihu.com",
    # add more if needed
}

# WebScrapingAPI credentials (you can also set this in your env)
WSA_API_KEY = os.getenv("WSA_API_KEY")
WSA_HOST    = "api.webscrapingapi.com"

## Brave
TRACKING_KEYS = {
    "utm_source","utm_medium","utm_campaign","utm_term","utm_content",
    "gclid","gbraid","wbraid","fbclid","msclkid","ocid","cvid","form","spm","ved","ei","oq","sxsrf","sca_esv","ntb"
}

def _drop_tracking_params(url: str) -> str:
    try:
        p = urlparse(url)
        q = parse_qs(p.query, keep_blank_values=True)
        q = {k: v for k, v in q.items() if k not in TRACKING_KEYS and not k.startswith("utm_")}
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q, doseq=True), p.fragment))
    except Exception:
        return url

def resolve_brave_redirect(href: str) -> str:
    """
    Brave result links are typically direct (no redirect hop).
    Still, we normalize & strip tracking params like in your Bing helper.
    """
    try:
        return _drop_tracking_params(href)
    except Exception:
        return href


def fetch_brave_results(query, start, batch_size):
    """
    Fetch one page of *organic* Brave Search results via WebScrapingAPI.
    Returns up to batch_size (title, link) tuples, skipping excluded domains.

    Brave SERP markup:
      - Each organic result is a <div class="snippet" data-type="web"> … </div>
      - The clickable title is the first <a href> inside that snippet.
    """
    # Build a Brave URL (server-rendered; no JS needed)
    brave_url = (
        "https://search.brave.com/search?"
        + urllib.parse.urlencode({
            "q": query,
            **({"offset": start-1} if start > 1 else {}), # use ** to unpack result of if condition. If not first page send offset other wise dont send offset peram, brave will assume its first page. This helps in brave not blocking you for scraping. 
            # "count": batch_size, # Brave seems to not find any indexs when you use this peram even though it is in there api documentation, thankfully we dont really need it. Assume 20 index per page for brave. 
            "source": "web"
        })
    )

    # Proxied request through WebScrapingAPI
    conn = http.client.HTTPSConnection(WSA_HOST)
    params = urllib.parse.urlencode({
        "api_key": WSA_API_KEY,
        "url": brave_url,
        "render_js": False,   # SSR HTML contains results; no need for JS
        # "country": "us",
    })
    conn.request("GET", f"/v2?{params}")
    resp = conn.getresponse()
    html = resp.read().decode("utf-8")

    results = get_result_urls_from_html(html=html)

    # soup = BeautifulSoup(html, "html.parser")
    # results = []

    # # Organic web results only
    # for snip in soup.select('div.snippet[data-type="web"]')[:batch_size]:
    #     print("found\n")
    #     a = snip.find("a", href=True)
    #     if not a:
    #         continue

    #     title = a.get_text(strip=True)
    #     link = _drop_tracking_params(a["href"])  # Brave gives direct links; still clean params

    #     # domain exclusion logic
    #     domain = urlparse(link).netloc.lower()
    #     if domain in EXCLUDED_DOMAINS:
    #         # print(f"Domain Excluded: {domain}")
    #         continue

    #     results.append((title, link))

    # time.sleep(random.uniform(*delay_range))  # be nice, if you want
    return results



def scrape_brave_to_csv(query, output_file, max_results, page_size):
    """
    Iterate Brave pages using the 0-based 'offset' (page_index).
    """
    if os.path.exists(output_file):
        os.remove(output_file)

    total_written = 0
    header_written = False
    page_index = 1

    # OVERRIDE USER
    page_size = 20

    while total_written < max_results:
        try:
            batch = fetch_brave_results(query, page_index, page_size)
            if not batch:
                print(f"No more results at page {page_index}. Stopping.")
                break

            with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                if not header_written:
                    writer.writerow(["Page Title", "URL"])
                    header_written = True

                for title, link in batch:
                    writer.writerow([title, link])
                    total_written += 1
                    if total_written >= max_results:
                        break

            print(f"Fetched & saved {len(batch)} items from page {page_index} (total {total_written}).")

            page_index += 1
        except Exception as e:
            print(f"Error on page {page_index}: {e}. Retrying after delay.")
        time.sleep(random.uniform(*delay_range))

    print(f"\nDone! {total_written} total results saved to {output_file}")


def _extract_balanced_object(text: str, start_index: int) -> str:
    depth = 0
    i = start_index
    in_string = False
    quote = None
    escape = False

    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start_index:i+1]
        i += 1

    raise ValueError("Unbalanced braces while extracting object.")

def get_result_urls_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script"):

        txt = script.string or script.text or ""
        idx = txt.find("web:")
        if idx == -1:
            continue

        brace_idx = txt.find("{", idx)
        if brace_idx == -1:
            continue

        web_obj_text = _extract_balanced_object(txt, brace_idx)

        # Normalize common JS-only tokens so JSON5 can parse it
        cleaned = web_obj_text
        # Replace `void 0` and `undefined` with null
        cleaned = re.sub(r"\bvoid\s+0\b", "null", cleaned)
        cleaned = re.sub(r"\bundefined\b", "null", cleaned)

        # Optional: remove trailing commas before } or ]
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

        try:
            web_obj = json5.loads(cleaned)
        except Exception as e:
            raise RuntimeError(f"Failed to parse `web` object: {e}")

        results = web_obj.get("results")
        if isinstance(results, list):
            urls = []
            for item in results:
                if isinstance(item, dict) and "url" in item and isinstance(item["url"], str):
                    urls.append((item["title"],item["url"]))
            return urls

    # If we get here, nothing matched.
    return []
