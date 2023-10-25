"""
Purpose: Scrape links that were missed by the `scrape_politifact_all.py` script

Input: None. Paths/files are hardcoded.

Output: .parquet file like that created with `scrape_politifact_all.py`

Author: Matthew DeVerna
"""
import json
import os
import random
import time

import pandas as pd

from politifact_pkg import PolitiFactCheck
from politifact_pkg.utils import fetch_url

# Politifact URLS
POLITIFACT_BASE_URL = "https://www.politifact.com"
FC_LIST_URL = f"{POLITIFACT_BASE_URL}/factchecks/?page="

# Paths and files
DATA_DIR = "../data"
FC_CACHE = os.path.join(DATA_DIR, "missed_factchecks_cache.json")
FC_PARQUET = os.path.join(DATA_DIR, "missed_factchecks.parquet")
MISSED_LINKS = os.path.join(DATA_DIR, "missed_factcheck_links.txt")


if __name__ == "__main__":
    # Read all of the missed links into a list
    all_links = []
    with open(MISSED_LINKS, "r") as f:
        for line in f:
            all_links.append(line.strip())

    # Fetch all of the links
    print("Fetching all of the links...")
    fact_checks = []
    with open(FC_CACHE, "a") as f:
        for link in all_links:
            print(f"\t- {link}")
            try:
                time.sleep(0.5 + random.random())
                response = fetch_url(link)
                fc = PolitiFactCheck(response=response, link=link)
                fc_dict = {
                    key: value
                    for key, value in vars(fc).items()
                    if not key.startswith("_")
                }
                fc_dict["page"] = -1  # Mark -1 to indicate that we don't know the page
                fact_checks.append(fc_dict)
                f.write(json.dumps(fc_dict) + "\n")
            except Exception as e:
                print(f"\t- Failed link: {link}")
                print(e)

    # Create a dataframe and save as parquet
    fc_df = pd.DataFrame.from_records(fact_checks)
    fc_df.to_parquet(FC_PARQUET)

    # Provide some stats
    print(f"Scraped {len(fc_df)} fact checks.")

    print("--- Scraping complete ---")
