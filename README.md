# politifact-scraper
Scrape fact-checks from politifact.com


### Contents
- `data/`: stores scraped data
- `package/`: local package utilized by the `scritps/`. See `package/README.md` for how to install.
- `scripts/`: scripts for scraping data. Eventually, there will be one script that scrapes the entire list of PolitiFact fact checks and then another script that updates the existing list with the newest ones. The latter will be designed to run periodically with a cronjob so it is always up to date. Note that this does not mean the dataset in this repository is up to date!