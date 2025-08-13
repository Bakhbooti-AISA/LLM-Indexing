#!/usr/bin/env python3
"""
Script to extract search strings and cited URLs from HAR files and place metadata files
into their corresponding network-logs-prompt-* result directories based on prompt ID.

Usage:
    python har_results_annotator.py --har-dir /path/to/har_dir \
                                 --results-root /path/to/results_root

For each HAR named:
    network-logs-prompt-<ID>_<TIMESTAMP>.har
it finds the directory under results_root starting with:
    network-logs-prompt-<ID>_
and writes `<har_basename>_meta.json` into that folder.
"""
import os
import json
import argparse
from typing import List, Dict, Any

# Placeholder imports; replace with your implementations
from chatgpt_scraper.har_parser import parse_entry, parse_sse_stream, extract_search_queries, extract_urls


def process_har_file(har_path: str) -> Dict[str, Any]:
    """
    Process a single HAR file to extract search_strings and cited_urls.
    """
    try:
        with open(har_path, 'r', encoding='utf-8') as f:
            har = json.load(f)
        entries = har.get('entries') or har.get('log', {}).get('entries', [])
        target = next(
            (e for e in entries if e.get('request', {}).get('url', '').endswith('/conversation')),
            None
        )
        if not target:
            raise ValueError("No conversation entry found in HAR")

        metrics = parse_entry(target)
        events = parse_sse_stream(metrics.get('content_text', ''))
        queries = extract_search_queries(events)
        _, _, _, cited = extract_urls(events)

        return {'search_strings': queries, 'cited_urls': cited}
    except Exception as e:
        return {'error': str(e)}


def find_matching_dir(results_root: str, base_name: str) -> str:
    """
    Given a HAR base name like 'network-logs-prompt-39_20250805_025105',
    find a directory under results_root that starts with 'network-logs-prompt-39_'.
    Returns the full path or an empty string if not found.
    """
    # Extract prefix up to the first underscore
    prefix = base_name.split('_', 1)[0] + '_'
    for entry in os.listdir(results_root):
        full_path = os.path.join(results_root, entry)
        if os.path.isdir(full_path) and entry.startswith(prefix):
            return full_path
    return ''


def main(har_dir: str, results_root: str):
    har_files = [os.path.join(har_dir, fn)
                 for fn in os.listdir(har_dir)
                 if fn.lower().endswith(('.har', '.json'))]
    if not har_files:
        print(f"No HAR files found in {har_dir}")
        return

    for har_path in har_files:
        base = os.path.splitext(os.path.basename(har_path))[0]
        target_dir = find_matching_dir(results_root, base)
        if not target_dir:
            print(f"Warning: no matching results folder for {base} under {results_root}")
            continue

        meta = process_har_file(har_path)
        out_filename = f"{base}_meta.json"
        out_path = os.path.join(target_dir, out_filename)
        with open(out_path, 'w', encoding='utf-8') as outf:
            json.dump(meta, outf, indent=2)
        print(f"Wrote metadata to {out_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Annotate HARs with search strings and cited URLs into result dirs"
    )
    parser.add_argument('--har-dir', required=True, help='Directory containing HAR files')
    parser.add_argument('--results-root', required=True, help='Root directory under which network-logs-prompt-* folders reside')
    args = parser.parse_args()
    main(args.har_dir, args.results_root)