"""
Purpose: Scrape all of the fact checks on the PolitiFact website.

Input: None. Paths/files are hardcoded.

Output: .parquet file with the below columns:
    - verdict: The fact-checking verdict.
        - Options: 'true', 'mostly-true', 'half-true', 'mostly-false', 'false', 'pants-on-fire'
    - statement: The statement.
    - statement_originator: The statement originator.
    - statement_date: The date the statement was made.
    - factchecker_name: The name of the fact checker.
    - factcheck_date: The date of the fact check.
    - topics: The topics of the fact check.
    - factcheck_analysis_link: The URL of the fact check.

Author: Matthew DeVerna
"""

import json
import os
import random
import time

import datetime as dt
import pandas as pd

from politifact_pkg import PolitiFactCheck
from politifact_pkg.utils import fetch_url, find_max_page
from politifact_pkg.parsing import extract_statement_links

#### IMPORTANT!!! ####
# Set to some number that is higher than the number of pages of fact checks
MAX_PAGE = 850

# Politifact URLS
POLITIFACT_BASE_URL = "https://www.politifact.com"
FC_LIST_URL = f"{POLITIFACT_BASE_URL}/factchecks/?page="

# Ensure the script runs from the the current directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Output paths
DATA_DIR = "../data"
os.makedirs(DATA_DIR, exist_ok=True)

FC_CACHE = os.path.join(DATA_DIR, "factchecks_cache.jsonl")
FC_PARQUET = os.path.join(
    DATA_DIR, f"{dt.datetime.now().strftime('%Y-%m-%d')}_factchecks.parquet"
)
MISSED_LINKS = os.path.join(DATA_DIR, "missed_factcheck_links.txt")


if __name__ == "__main__":
    print("Check if we already have cached fact checks...")

    fact_checks = []  # Will store fact checks here for .parquet file
    page_num = 1  # Counter for pages
    if os.path.exists(FC_CACHE):
        print("Loading cached fact checks...")
        with open(FC_CACHE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        fc_dict = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"Problematic line: {line}")
                        raise e
                    fact_checks.append(fc_dict)

    collected_links = set([fc["factcheck_analysis_link"] for fc in fact_checks])

    print(f"\t- Found {len(fact_checks)} fact checks already collected.")

    print("Finding the maximum page number...")
    max_page = find_max_page(base_url=FC_LIST_URL, max_page=MAX_PAGE)
    print(f"\t- Found max page: {max_page}")

    print("Begin scraping new fact checks...")
    with open(FC_CACHE, "a") as f:
        for page_num in range(1, max_page + 1):
            print(f"Fetching page {page_num}...")
            page_url = f"{FC_LIST_URL}{page_num}"

            # Keep trying more politifact pages until we get a None, meaning we've
            # reached the end of the list of fact-checks of we are running into other errors.
            response = fetch_url(page_url)
            if response is None:
                print("Failed to fetch page.")
                print(f"\t- {page_url}")
                print("BREAKING SCRIPT.")
                break

            print(f"\t- Parsing fact checks...")
            statement_links = extract_statement_links(response, FC_LIST_URL)
            print(f"\t- Found {len(statement_links)} links.")

            for idx, link in enumerate(statement_links, start=1):
                full_url = f"{POLITIFACT_BASE_URL}{link}"

                if full_url in collected_links:
                    print(f"\t- {idx}. Already collected. Skipping.")
                    continue

                time.sleep(0.5 + random.random())  # Be nice.

                try:
                    print(f"\t- {idx}. Fetching {full_url}")
                    response = fetch_url(full_url)

                    # This class automatically extracts the relvant information
                    # see the data_models.py file for details
                    fc = PolitiFactCheck(response=response, link=full_url)

                except Exception as e:
                    print(f"\t- Failed. Saving to missed file.")
                    print(e)
                    with open(MISSED_LINKS, "a") as mf:
                        mf.write(f"{full_url}\n")
                    continue

                print(f"\t\t- Success.")

                # Extract all of the properties into a dict
                fc_dict = {
                    key: value
                    for key, value in vars(fc).items()
                    if not key.startswith("_")
                }

                fc_dict["page"] = page_num

                # Store the fact checks in a .json file incase the script is broken
                f.write(json.dumps(fc_dict) + "\n")

                fact_checks.append(fc_dict)

    fc_df = pd.DataFrame.from_records(fact_checks)

    # The caching procedure will create duplicates so we drop them here
    fc_df.drop_duplicates(inplace=True)
    fc_df.to_parquet(FC_PARQUET)

    # Provide some stats
    print(f"Scraped {len(fc_df)} fact checks.")

    print("--- Scraping complete ---")
