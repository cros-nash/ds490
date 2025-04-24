#!/usr/bin/env python3

"""
Scraper template with parameters for pagination, delay, max pages, timeout, and robots.txt.
Placeholders marked by {{...}} should be filled by the LLM or user input.
"""

import sys
import time
import requests
from bs4 import BeautifulSoup
import json
import csv

def can_crawl(url):
    """
    Placeholder for robots.txt checking logic.
    If {{ RESPECT_ROBOTS }} is true, add code to parse and respect robots.txt.
    For simplicity, returns True here by default.
    """
    # >>> BEGIN ROBOTS_LOGIC
    # {{ RESPECT_ROBOTS }}
    # <<< END ROBOTS_LOGIC
    return True

def fetch_html(url, snippet, timeout):
    """
    Return HTML content from a snippet if provided; otherwise fetch from URL with user-agent.
    """
    snippet = snippet.strip()
    if snippet:
        return snippet
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"Error: {e}")
        sys.exit(1)

def parse_page(html):
    """
    Parse a single page of HTML. This function extracts data from the current page only.
    """
    soup = BeautifulSoup(html, "html.parser")
    data = []

    # >>> BEGIN EXTRACTION_LOGIC
    # {{ EXTRACTION_LOGIC }}
    # <<< END EXTRACTION_LOGIC

    return data

def find_next_page(soup):
    """
    Placeholder function to detect the 'next page' URL or construct the next page link.
    Return None if there's no next page. The LLM can fill this logic if needed.
    """
    # >>> BEGIN PAGINATION_LOGIC
    # {{ PAGINATION_LOGIC }}
    # <<< END PAGINATION_LOGIC
    return None  # Default if not implemented

def scrape_all_pages(url, snippet, delay, max_pages, timeout):
    """
    Orchestrates multi-page scraping. Checks robots.txt if enabled.
    """
    all_data = []
    page_count = 0
    current_url = url

    # If snippet is non-empty, we won't page since snippet is static HTML
    # If snippet is empty, we attempt multi-page scraping
    while True:
        # If user wants to respect robots.txt, check it before requesting any new URL
        if not can_crawl(current_url):
            print(f"Robots.txt disallows crawling {current_url}")
            break

        html = fetch_html(current_url, snippet, timeout)
        soup = BeautifulSoup(html, "html.parser")

        # Parse current page
        page_data = parse_page(html)
        all_data.extend(page_data)

        page_count += 1
        if page_count >= max_pages:
            print("Reached max pages limit.")
            break

        # Find next page (if any). If there's no 'Next' link, break.
        next_page_url = find_next_page(soup)
        if not next_page_url:
            break

        # Delay before fetching the next page
        time.sleep(delay)
        current_url = next_page_url

        # If snippet was provided, we never do another page
        if snippet.strip():
            break

    return all_data

def output_results(data, fmt):
    """
    Output data in JSON or CSV format.
    """
    fmt = fmt.lower().strip()
    if fmt not in ("json", "csv"):
        print("Invalid or unspecified output format. Please choose 'json' or 'csv'.")
        sys.exit(1)

    if fmt == "json":
        # >>> BEGIN JSON_OUTPUT
        # {{ JSON_OUTPUT_LOGIC }}
        # <<< END JSON_OUTPUT
    elif fmt == "csv":
        # >>> BEGIN CSV_OUTPUT
        # {{ CSV_OUTPUT_LOGIC }}
        # <<< END CSV_OUTPUT

def main():
    # >>> META_COMMENTS
    # {{ META_COMMENTS }}
    # <<< META_COMMENTS

    url = "{{ URL }}"
    snippet = """{{ HTML_SNIPPET }}"""
    output_format = "{{ OUTPUT_FORMAT }}"
    # Delay between requests, in seconds
    delay = #{{ DELAY }}
    # Max pages to visit
    max_pages = #{{ MAX_PAGES }}
    # Request timeout in seconds
    timeout = #{{ TIMEOUT }}

    data = scrape_all_pages(url, snippet, delay, max_pages, timeout)
    output_results(data, output_format)

if __name__ == "__main__":
    main()
