"""
Purpose: Scrape all of the fact checks on the PolitiFact website.

Input: None

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
import requests
import time

import pandas as pd

from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from politifact_pkg import PolitiFactCheck

#### IMPORTANT!!! ####
# Set to some number that is higher than the number of pages of fact checks
MAX_PAGE = 800

# Politifact URLS
POLITIFACT_BASE_URL = "https://www.politifact.com"
FC_LIST_URL = f"{POLITIFACT_BASE_URL}/factchecks/?page="

# Output paths
DATA_DIR = "../data"
FC_CACHE = os.path.join(DATA_DIR, "factchecks_cache.json")
FC_PARQUET = os.path.join(DATA_DIR, "factchecks.parquet")
MISSED_LINKS = os.path.join(DATA_DIR, "missed_factcheck_links.txt")


def fetch_url(url, max_retries=7, retry_delay=2):
    """
    Fetches data for a provided web URL.

    Parameters
    ----------
    - url (str): The URL of the webpage.
    - max_retries (int): Maximum number of retries in case of failure.
    - retry_delay (int): Number of seconds to wait between retries.

    Returns
    ----------
    - str: The HTML content of the webpage, or None in case of failure.

    Exceptions
    ----------
    - TypeError
    """
    if not isinstance(url, str):
        raise TypeError("`url` must be a string")
    if not isinstance(max_retries, int):
        raise TypeError("`max_retries` must be an integer")
    if not isinstance(retry_delay, int):
        raise TypeError("`retry_delay` must be an integer")

    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response

        except RequestException as e:
            if isinstance(e, requests.ConnectionError):
                # Handle network-related errors
                print(f"Attempt {attempt + 1} failed due to a network error: {e}")
            elif isinstance(e, requests.Timeout):
                # Handle timeout errors
                print(f"Attempt {attempt + 1} timed out: {e}")
            else:
                # Handle other RequestException errors
                print(f"Attempt {attempt + 1} failed with an unknown error: {e}")

            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay * attempt)
            else:
                print("Max retries reached. Failed to fetch the webpage.")
                return None


def find_no_results(soup):
    """
    Check if a politifact page has no results.

    Parameters:
    ----------
    - soup (BeautifulSoup): HTML content of the webpage.

    Returns:
    ----------
    - bool: True if the page has no results, False otherwise.
    """
    # Find the <h2> element with the specified class.
    h2_element = soup.find("h2", class_="c-title c-title--subline")

    # Check if the element exists and contains the expected text.
    if h2_element and "No Results found" in h2_element.get_text():
        return True
    else:
        return False


def find_max_page(base_url, max_page):
    """
    Find the maximum page number for the politifact base URL.

    Parameters:
    ----------
    - base_url (str): The base URL used to construct the politifact URLs.
    - max_page (int): The maximum page number to search.

    Returns:
    ----------
    - int: The maximum page number with politifact results.

    """
    no_results = True

    while no_results and max_page > 0:
        # Decrement max_page by 1
        max_page -= 1

        # Sleep for a bit to be nice to politifact
        time.sleep(0.3 + random.random())

        # Construct the URL
        url = f"{base_url}{max_page}"

        # Fetch the page
        print(f"Trying: {url}")
        response = fetch_url(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Once this returns False, we have found results, and should take
        # this as our maximum page.
        no_results = find_no_results(soup)

    return max_page


def extract_statement_links(response):
    """
    Extracts links from requests.models.Response object from politifact.

    Parameters:
    ----------
    - response (requests.models.Response): HTML content of the webpage.

    Returns:
    ----------
    - statement_links (List(str)): A list of extracted href attributes.

    Exceptions
    ----------
    - TypeError
    """
    if not isinstance(response, requests.models.Response):
        raise TypeError(f"`response` must be of type `requests.models.Response`")
    if not response.url.startswith(FC_LIST_URL):
        raise TypeError(
            f"`response` URL must start with {FC_LIST_URL}. "
            f"Currently URL is: {response.url}"
        )

    statement_links = []
    if response:
        html_text = response.text
        soup = BeautifulSoup(html_text, "html.parser")

        # Find all elements with the "m_statement__quote" class
        statement_divs = soup.find_all("div", attrs={"class": "m-statement__quote"})

        for element in statement_divs:
            # Extract the href attribute if it exists
            href = element.find("a").get("href")
            if href:
                statement_links.append(href)

    return statement_links


if __name__ == "__main__":
    print("Check if we already have cached fact checks...")

    fact_checks = []  # Will store fact checks here for .parquet file
    page_num = 1  # Counter for pages
    if os.path.exists(FC_CACHE):
        print("Loading cached fact checks...")
        with open(FC_CACHE, "r") as f:
            for line in f:
                fc_dict = json.loads(line)
                fact_checks.append(fc_dict)
                page_num = max(page_num, fc_dict["page"])

    print(f"\t- Found {len(fact_checks)} fact checks.")

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
            statement_links = extract_statement_links(response)
            print(f"\t- Found {len(statement_links)} links.")

            for idx, link in enumerate(statement_links, start=1):
                full_url = f"{POLITIFACT_BASE_URL}{link}"
                time.sleep(0.5 + random.random())

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
                        mf.write(f"{link}\n")
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
                f.write(f"{json.dumps(fc_dict)}\n")

                fact_checks.append(fc_dict)

    fc_df = pd.DataFrame.from_records(fact_checks)

    # The caching procedure will create duplicates so we drop them here
    fc_df.drop_duplicates(inplace=True)
    fc_df.to_parquet(FC_PARQUET)

    # Provide some stats
    print(f"Scraped {len(fc_df)} fact checks.")

    print("--- Scraping complete ---")
