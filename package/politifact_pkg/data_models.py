"""
PolitiFact data models for processing fact check analyses webpages.

Example fact check:
- https://www.politifact.com/factchecks/2007/oct/02/mike-gravel/yes-in-theory-but-not-in-practice/
"""
import re
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse

# Define the components of the date pattern using f-strings
MONTH_NAMES = "|".join(
    [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
)

DAY_PATTERN = r"\d{1,2}"
YEAR_PATTERN = r"\d{4}"

# Use an f-string to construct the final date pattern
DATE_PATTERN = rf"\b(?:{MONTH_NAMES})\s+{DAY_PATTERN},\s+{YEAR_PATTERN}"


class PolitiFactCheck:
    def __init__(self, response=None, link=None):
        """
        Ingest a requests.models.Response object for a PolitiFact factchecking page.
        """
        if not isinstance(response, requests.models.Response):
            raise TypeError(f"`response` must be of type `requests.models.Response`")
        if not isinstance(link, str):
            raise TypeError(f"`link` must be a string")

        result = urlparse(link)
        if not all([result.scheme, result.netloc]):
            raise TypeError("`link` must be a valid URL")

        # Internal proporties
        self._text = response.text
        self._soup = BeautifulSoup(self._text, parser="html.parser", features="lxml")
        self._factchecker_tag = self._get_factchecker_tag()

        # Public properties
        self.verdict = self._get_verdict()
        self.statement = self._get_statement()
        self.statement_originator = self._get_statement_originator()
        self.statement_date = self._get_statement_date()
        self.factchecker_name = self._get_factchecker_name()
        self.factcheck_date = self._get_factcheck_date()
        self.topics = self._get_topics()
        self.factcheck_analysis_link = link
        self.date_retrieved = datetime.utcnow().timestamp()

    def _get_factchecker_tag(self):
        """Return the entire fact checker tag"""
        return self._soup.find("div", attrs={"class": "m-author__content"})

    def _get_factchecker_name(self):
        """Return the fact checkers name"""
        return self._factchecker_tag.find("a").text

    def _get_factcheck_date(self):
        """Return the date of the fact check"""
        text = self._factchecker_tag.find("span").text
        return self._extract_date_string(text)

    def _get_verdict(self):
        """Return the fact-checking verdict"""
        images = self._soup.find_all("img", attrs={"class": "c-image__original"})
        for image in images:
            verdict_image_link = image.get("src")
            if verdict_image_link and "rulings" in verdict_image_link:
                # Return the first image containing "rulings"
                # URL example: https://static.politifact.com/politifact/rulings/meter-mostly-false.jpg
                basename = verdict_image_link.split("/")[-1]
                return basename.split(".")[0].replace("meter-", "")

    def _get_statement(self):
        """Return the statement"""
        return self._soup.find(
            "div", attrs={"class": "m-statement__quote"}
        ).text.replace("\n", "")

    def _get_statement_originator(self):
        """Return the statement originator"""
        return self._soup.find("a", attrs={"class": "m-statement__name"}).get("title")

    def _get_statement_date(self):
        """Return the date the statement was made."""
        text = self._soup.find("div", attrs={"class": "m-statement__desc"}).text
        return self._extract_date_string(text)

    def _extract_date_string(self, string):
        """
        Return a date string from a string.

        Format of date within string should be something like "September 26, 2007"
        """
        # Use re.search to find the date in the text
        match = re.search(DATE_PATTERN, string)

        # Use re.search to find the date in the text
        match = re.search(DATE_PATTERN, string)

        if match:
            return match.group(0)

    def _get_topics(self, delimiter="|"):
        """Return the topics of the fact check"""
        topic_list = self._soup.find(
            "ul", attrs={"class": "m-list m-list--horizontal"}
        ).find_all("li", attrs={"class": "m-list__item"})

        topics = []
        for topic_item in topic_list:
            topics.append(topic_item.find("span").text)
        return f"{delimiter}".join(topics)
