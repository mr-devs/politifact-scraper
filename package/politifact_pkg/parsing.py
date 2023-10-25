"""
Functions for parsing PolitiFact webpages.
"""
import requests

from bs4 import BeautifulSoup


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


def extract_statement_links(response, url_base):
    """
    Extracts links from requests.models.Response object from politifact.

    Parameters:
    ----------
    - response (requests.models.Response): HTML content of the webpage.
    - url_base (str): The base URL used to construct the politifact URLs.

    Returns:
    ----------
    - statement_links (List(str)): A list of extracted href attributes.

    Exceptions
    ----------
    - TypeError
    """
    if not isinstance(response, requests.models.Response):
        raise TypeError(f"`response` must be of type `requests.models.Response`")
    if not response.url.startswith(url_base):
        raise TypeError(
            f"`response` URL must start with {url_base}. "
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
