import os
import glob
import csv
import json

# --- Helper functions ---

def load_text_urls(txt_path: str) -> list:
    """
    Read target URLs from a text file.
    """
    with open(txt_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def load_csv_results(csv_paths: list) -> list:
    """
    From a list of CSV paths, collect entries with page title, URL, and rank, grouped by search query.
    Returns list of tuples (query_idx, entries), where entries is list of dicts:
      { 'page_title': str, 'url': str, 'rank': int, 'search_string_num': int }
    """
    grouped = []
    for q_idx, csv_path in enumerate(csv_paths, start=1):
        entries = []
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for rank, row in enumerate(reader, start=1):
                url = row.get('URL', '').strip()
                title = row.get('Page Title', '').strip()
                if not url:
                    continue
                entries.append({
                    'page_title': title,
                    'url': url,
                    'rank': rank,
                    'search_string_num': q_idx
                })
        grouped.append((q_idx, entries))
    return grouped


def find_network_log_dirs(root: str, categories: list) -> list:
    """
    Return list of (dir_path, category) for each network-logs-prompt-* under categories.
    """
    dirs = []
    for cat in categories:
        path = os.path.join(root, cat)
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            if name.startswith('network-logs-prompt-') and os.path.isdir(os.path.join(path, name)):
                dirs.append((os.path.join(path, name), cat))
    return dirs

# --- Main routine to build nested JSON ---
from typing import Dict, List

from pathlib import Path

def build_structure(root_dir: str = '.', categories: list = None) -> dict:
    """
    Construct nested dict in format:
    {
      category: {
        set_id: {
          'urls_from_prompt': [...],
          'urls_cited': [...],       # <- from new meta 'cites' (or old 'cited_urls')
          'search_string': [...],
          'bing_urls': [...],
          'google_urls': [...]
        },
        ...
      },
      ...
    }
    """
    # If not provided, auto-discover categories (handles *_gpt-5 etc.)
    if categories is None:
        categories = [
            p.name for p in Path(root_dir).iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]

    aggregated: Dict[str, Dict[str, Dict[str, List[str]]]] = {}

    # Uses your existing helper to enumerate result dirs under categories
    for set_path, category in find_network_log_dirs(root_dir, categories):
        set_id = os.path.basename(set_path)
        aggregated.setdefault(category, {})

        # 1) URLs from prompt (unchanged)
        txt_files = glob.glob(os.path.join(set_path, 'urls_to_eval_*.txt'))
        prompt_urls = load_text_urls(txt_files[0]) if txt_files else []

        # 2) Load HAR metadata (NEW first: query_meta.json; fallback: old *_meta.json)
        meta = None
        new_meta_path = os.path.join(set_path, 'query_meta.json')
        old_meta_glob = glob.glob(os.path.join(set_path, '*_meta.json'))

        if os.path.exists(new_meta_path):
            try:
                with open(new_meta_path, 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
            except Exception:
                meta = None
        elif old_meta_glob:
            try:
                with open(old_meta_glob[0], 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
            except Exception:
                meta = None

        # Map new schema -> old output names (and keep backward compatibility)
        urls_cited = []
        search_strings = []
        if isinstance(meta, dict):
            # New schema preferred
            #   top-level: meta['cites'], meta['search_strings']
            #   per-HAR:  meta['hars'][0]['cites'] (backup if needed)
            search_strings = meta.get('search_strings', [])
            urls_cited = meta.get('cites', [])

            if not urls_cited:
                # Try per-HAR (single HAR per results dir)
                try:
                    urls_cited = (meta.get('hars') or [{}])[0].get('cites', []) or []
                except Exception:
                    urls_cited = []

            # Back-compat with older annotator JSON
            if not urls_cited:
                urls_cited = meta.get('cited_urls', [])
            if not search_strings:
                search_strings = meta.get('search_strings', [])  # same key in old schema

        # 3) CSVs for queries (unchanged)
        all_csvs = sorted(glob.glob(os.path.join(set_path, '*.csv')))
        bing_csvs = [p for p in all_csvs if 'bing' in os.path.basename(p).lower()]
        google_csvs = [p for p in all_csvs if 'google' in os.path.basename(p).lower()]

        bing_grouped = load_csv_results(bing_csvs)
        google_grouped = load_csv_results(google_csvs)

        # Flatten grouped into lists
        bing_entries = [entry for _, entries in bing_grouped for entry in entries]
        google_entries = [entry for _, entries in google_grouped for entry in entries]

        # 4) Assemble
        aggregated[category][set_id] = {
            'urls_from_prompt': prompt_urls,
            'urls_cited': urls_cited,       # from new 'cites' (or old 'cited_urls')
            'search_string': search_strings,
            'bing_urls': bing_entries,
            'google_urls': google_entries
        }

    return aggregated


def save_structure_to_json(data: dict, filename: str = 'aggregated_data.json'):
    """
    Save nested dict to a JSON file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Saved aggregated data to {filename}")


if __name__ == '__main__':
    structured = build_structure()
    save_structure_to_json(structured)