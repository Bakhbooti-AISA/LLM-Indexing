import argparse
import os
import json
from datetime import datetime

from serp_scrapers.bing_scraper import scrape_bing_to_csv
from serp_scrapers.google_scraper import scrape_google_to_csv  # if available
from evaluators.evaluation import check_urls  # URL evaluation helper


def parse_args():
    parser = argparse.ArgumentParser(description="Unified SERP scraper CLI")
    parser.add_argument(
        '-q', '--queries', nargs='+', default=[],
        help='List of search queries to run'
    )
    parser.add_argument(
        '-f', '--queries-file', type=argparse.FileType('r'),
        help='Path to a JSON file containing a list of queries'
    )
    parser.add_argument(
        '-m', '--max-se-index', type=int, default=0,
        help='Maximum index the search engine scraper will scrape up to'
    )
    parser.add_argument(
        '-i', '--index-interval', type=int, default=50, choices=range(1, 51), metavar='[1-50]',
        help='Interval at which to scrape indexes (1-50)'
    )
    parser.add_argument(
        '-s', '--search-engines', nargs='+', default=['bing', 'google'],
        choices=['bing', 'google', 'duckduckgo', 'yahoo'],
        help='Which search engines to use (choose one or more)'
    )
    parser.add_argument(
        '-o', '--output-dir', default='outputs',
        help='Directory where query folders and CSV files will be saved'
    )
    parser.add_argument(
        '-t', '--txt-eval-file', default='urls.txt',
        help='Path to the text file containing URLs to evaluate against CSV results'
    )
    return parser.parse_args()


def load_queries(cli_queries, file_handle):
    queries = []
    if file_handle:
        data = json.load(file_handle)
        if not isinstance(data, list):
            raise ValueError("JSON must contain a list of query strings")
        queries.extend(data)
    queries.extend(cli_queries)
    return queries


def main():
    args = parse_args()
    queries = load_queries(args.queries, args.queries_file)
    os.makedirs(args.output_dir, exist_ok=True)

    for query in queries:
        # timestamp folder per query start
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_query = query.replace(' ', '_')
        query_folder = os.path.join(args.output_dir, f"{safe_query}_{timestamp}")
        os.makedirs(query_folder, exist_ok=True)

        print(f"Starting scrape for '{query}' at {timestamp}, saving in '{query_folder}'")

        # Save the original query text to a file
        query_txt = os.path.join(query_folder, "query.txt")
        with open(query_txt, 'w', encoding='utf-8') as f:
            f.write(query)

        csv_paths = []
        for engine in args.search_engines:
            output_path = os.path.join(
                query_folder,
                f"{engine}_{safe_query}.csv"
            )
            csv_paths.append(output_path)

            if engine == 'bing':
                scrape_bing_to_csv(
                    query=query,
                    output_file=output_path,
                    max_results=args.max_se_index,
                    batch_size=args.index_interval
                )
            elif engine == 'google':
                scrape_google_to_csv(
                    query=query,
                    output_file=output_path,
                    max_results=args.max_se_index,
                    page_size=args.index_interval
                )
            else:
                print(f"Engine '{engine}' not supported yet. Skipping.")

        # After scraping, evaluate URLs against scraped CSVs
        print(f"\nEvaluating URLs in '{args.txt_eval_file}' against scraped results...")
        results_filepath = os.path.join(query_folder, f"results_{timestamp}.txt")
        check_urls(csv_paths=csv_paths, txt_path=args.txt_eval_file, results_pathfile=results_filepath)
        print(f"Finished evaluation for '{query}'\n")

    print("All scrapes and evaluations completed.")


if __name__ == "__main__":
    main()
