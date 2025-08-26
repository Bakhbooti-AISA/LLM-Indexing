#!/usr/bin/env python3
"""
Write per-category lists of HAR files (absolute paths, one per line) showing
which have / haven't had Bing/Google scrapes.

Rules:
- If a HAR has **neither** Bing nor Google -> goes **only** to `missing_both__<category>.txt`.
- `missing_bing__<category>.txt` = has Google but not Bing (only-one-missing).
- `missing_google__<category>.txt` = has Bing but not Google (only-one-missing).
- `has_bing__<category>.txt` = any HAR with Bing results (regardless of Google).
- `has_google__<category>.txt` = any HAR with Google results (regardless of Bing).
- `unmatched_hars__<category>.txt` = HAR exists in datasets but no matching entry in aggregated.json.

Mapping:
  datasets/<category>/*hars*/network-logs-prompt-<ID>.har
  ↔ aggregated[<category>][set_id], where set_id begins with "network-logs-prompt-<ID>_" (timestamp ignored)

Usage:
  python per_category_scrape_status.py \
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
    ap = argparse.ArgumentParser(description="Per-category lists of HARs by Bing/Google scrape status.")
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

        has_bing: List[str] = []
        missing_bing: List[str] = []
        has_google: List[str] = []
        missing_google: List[str] = []
        missing_both: List[str] = []
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
            bing = entry.get("bing_urls", []) or []
            google = entry.get("google_urls", []) or []

            has_b = len(bing) > 0
            has_g = len(google) > 0

            # Always track "has" lists independently
            if has_b:
                has_bing.append(str(har))
            if has_g:
                has_google.append(str(har))

            # Missing logic per requirement:
            # - If neither -> only in missing_both
            # - If exactly one missing -> in that specific missing list
            if (not has_b) and (not has_g):
                missing_both.append(str(har))
            elif (not has_b) and has_g:
                missing_bing.append(str(har))
            elif has_b and (not has_g):
                missing_google.append(str(har))

        prefix = ds_cat
        write_lines(out_dir / f"has_bing__{prefix}.txt", has_bing)
        write_lines(out_dir / f"missing_bing__{prefix}.txt", missing_bing)
        write_lines(out_dir / f"has_google__{prefix}.txt", has_google)
        write_lines(out_dir / f"missing_google__{prefix}.txt", missing_google)
        write_lines(out_dir / f"missing_both__{prefix}.txt", missing_both)
        write_lines(out_dir / f"unmatched_hars__{prefix}.txt", unmatched)
        total_written += 6

    print(f"Wrote per-category lists to {out_dir} (files written: {total_written})")


if __name__ == "__main__":
    main()
