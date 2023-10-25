"""
Convenience functions for scraping the PolitiFact data.
"""
import random
import requests
import time

from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from politifact_pkg.parsing import find_no_results


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
