#!/usr/bin/env python3
"""
Write per-category lists of HAR files (absolute paths, one per line) showing
which have / haven't had Bing/Google/Brave scrapes.

Rules:
- If a HAR has **none** of Bing, Google, or Brave -> goes **only** to `missing_all__<category>.txt`.
- `missing_bing__<category>.txt`  = has **both** Google and Brave but **not** Bing (only-one-missing).
- `missing_google__<category>.txt`= has **both** Bing and Brave but **not** Google (only-one-missing).
- `missing_brave__<category>.txt` = has **both** Bing and Google but **not** Brave (only-one-missing).
- `has_bing__<category>.txt`   = any HAR with Bing results (regardless of others).
- `has_google__<category>.txt` = any HAR with Google results (regardless of others).
- `has_brave__<category>.txt`  = any HAR with Brave results (regardless of others).
- `unmatched_hars__<category>.txt` = HAR exists in datasets but no matching entry in aggregated.json.

Notes:
- We keep the "only-one-missing" semantics for the per-engine `missing_*` files, now generalized
  to three engines (i.e., exactly one missing, the other two present).
- If a HAR has exactly one or two engines present (but not all, not none), it will **not** appear
  in any `missing_*` list unless it matches the *only-one-missing* condition above. It will always
  appear in the corresponding `has_*` lists for whichever engines it has.

Mapping:
  datasets/<category>/*hars*/network-logs-prompt-<ID>.har
  ↔ aggregated[<category>][set_id], where set_id begins with "network-logs-prompt-<ID>_" (timestamp ignored)

Usage:
  python per_category_scrape_status_3engines.py \
    --aggregated /path/to/aggregated.json \
    --datasets-root /path/to/datasets \
    --output-dir /path/to/output_lists
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PREFIX = "network-logs-prompt-"

# Simple normalization for common category naming mismatch
CATEGORY_SYNONYMS = {
    "instramental": "instrumental",
    "instrumental": "instramental",
}

SEARCH_ENGINES = ("bing", "google", "brave")
URL_KEYS = {
    "bing": "bing_urls",
    "google": "google_urls",
    "brave": "brave_urls",
}

def load_aggregated(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def prompt_id_from_set_id(set_id: str) -> Optional[str]:
    # Expect forms like "network-logs-prompt-249_20250814_011917" or "network-logs-prompt-249"
    base = set_id.split("_", 1)[0]
    if not base.startswith(PREFIX):
        return None
    pid = base[len(PREFIX):]
    return pid if pid.isdigit() else None


def prompt_id_from_har_name(name: str) -> Optional[str]:
    # Expect exact file name: network-logs-prompt-<ID>.har
    if not name.startswith(PREFIX) or not name.endswith(".har"):
        return None
    pid = name[len(PREFIX):-4]
    return pid if pid.isdigit() else None


def index_aggregated(agg: Dict[str, Any]) -> Dict[str, Dict[str, Tuple[str, Dict[str, Any]]]]:
    """index[category][prompt_id] = (set_id, entry_dict)"""
    idx: Dict[str, Dict[str, Tuple[str, Dict[str, Any]]]] = {}
    for category, sets in agg.items():
        catmap: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        if not isinstance(sets, dict):
            continue
        for set_id, entry in sets.items():
            if not isinstance(entry, dict):
                continue
            pid = prompt_id_from_set_id(set_id)
            if not pid:
                continue
            # Last set_id wins if duplicates
            catmap[pid] = (set_id, entry)
        idx[category] = catmap
    return idx


def find_hars_in_category(datasets_root: Path, category: str) -> List[Path]:
    """Return all HARs under datasets/<category>/*hars*/network-logs-prompt-<ID>.har"""
    base = datasets_root / category
    if not base.exists():
        return []
    hars: List[Path] = []
    for sub in base.rglob("*.har"):
        if "hars" in sub.parent.name.lower() and prompt_id_from_har_name(sub.name):
            hars.append(sub.resolve())
    return sorted(hars)


def pick_aggregated_category(idx: Dict[str, Dict[str, Tuple[str, Dict[str, Any]]]], ds_cat: str) -> Optional[str]:
    if ds_cat in idx:
        return ds_cat
    syn = CATEGORY_SYNONYMS.get(ds_cat)
    if syn and syn in idx:
        return syn
    return None


def write_lines(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for line in sorted(lines):
            f.write(line + "\n")


def main():
    ap = argparse.ArgumentParser(description="Per-category lists of HARs by Bing/Google/Brave scrape status.")
    ap.add_argument("--aggregated", required=True, help="Path to aggregated.json")
    ap.add_argument("--datasets-root", required=True, help="Path to datasets root")
    ap.add_argument("--output-dir", default=None, help="Directory to write per-category files (default: alongside aggregated.json)")
    args = ap.parse_args()

    aggregated_path = Path(args.aggregated).resolve()
    datasets_root = Path(args.datasets_root).resolve()
    out_dir = Path(args.output_dir).resolve() if args.output_dir else aggregated_path.parent

    if not aggregated_path.exists():
        raise SystemExit(f"aggregated JSON not found: {aggregated_path}")
    if not datasets_root.exists():
        raise SystemExit(f"datasets_root not found: {datasets_root}")

    agg = load_aggregated(aggregated_path)
    idx = index_aggregated(agg)

    # Discover dataset categories by top-level folders under datasets/
    ds_categories = sorted([p.name for p in datasets_root.iterdir() if p.is_dir()])

    total_written = 0
    for ds_cat in ds_categories:
        agg_cat = pick_aggregated_category(idx, ds_cat)
        hars = find_hars_in_category(datasets_root, ds_cat)
        if not hars:
            continue

        # "has_*" lists (independent)
        has_lists: Dict[str, List[str]] = {engine: [] for engine in SEARCH_ENGINES}

        # "missing_*" lists (ONLY-ONE-MISSING: present in other two, absent in this one)
        missing_only_one: Dict[str, List[str]] = {engine: [] for engine in SEARCH_ENGINES}

        # Other buckets
        missing_all: List[str] = []
        unmatched: List[str] = []

        for har in hars:
            pid = prompt_id_from_har_name(har.name)
            if not pid:
                continue

            if not agg_cat:
                unmatched.append(str(har))
                continue

            set_info = idx.get(agg_cat, {}).get(pid)
            if not set_info:
                unmatched.append(str(har))
                continue

            _, entry = set_info

            # Presence booleans per engine
            present: Dict[str, bool] = {}
            for engine in SEARCH_ENGINES:
                urls = entry.get(URL_KEYS[engine], []) or []
                present[engine] = len(urls) > 0

            # Track has_* (independent)
            for engine, is_present in present.items():
                if is_present:
                    has_lists[engine].append(str(har))

            # Missing buckets
            num_present = sum(present.values())
            if num_present == 0:
                # none present → goes ONLY to missing_all
                missing_all.append(str(har))
            elif num_present == 2:
                # exactly one missing → drop into that specific engine's missing list
                for engine, is_present in present.items():
                    if not is_present:
                        missing_only_one[engine].append(str(har))
                        break
            # For num_present == 1 (two missing) or num_present == 3 (none missing),
            # we don't add to any missing_* list by design; has_* already records presence.

        prefix = ds_cat

        # Write has_* files
        write_lines(out_dir / f"has_bing__{prefix}.txt", has_lists["bing"])
        write_lines(out_dir / f"has_google__{prefix}.txt", has_lists["google"])
        write_lines(out_dir / f"has_brave__{prefix}.txt", has_lists["brave"])

        # Write missing (only-one-missing) files
        write_lines(out_dir / f"missing_bing__{prefix}.txt", missing_only_one["bing"])
        write_lines(out_dir / f"missing_google__{prefix}.txt", missing_only_one["google"])
        write_lines(out_dir / f"missing_brave__{prefix}.txt", missing_only_one["brave"])

        # Write missing_all & unmatched
        write_lines(out_dir / f"missing_all__{prefix}.txt", missing_all)
        write_lines(out_dir / f"unmatched_hars__{prefix}.txt", unmatched)

        # files written for this category
        total_written += 8  # 3 has_* + 3 missing_* + missing_all + unmatched

    print(f"Wrote per-category lists to {out_dir} (files written: {total_written})")


if __name__ == "__main__":
    main()
