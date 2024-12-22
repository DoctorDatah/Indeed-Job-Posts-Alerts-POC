from bs4 import BeautifulSoup  # For parsing HTML
import requests  # For fetching HTML (if needed)
import re
import os
import datetime

def extract_individual_job_blocks(soup):
    """
    Extract job postings by finding the nearest ancestor <tbody> or <table>
    for labels like 'days ago' or 'just posted'.

    Args:
        soup (BeautifulSoup): Parsed HTML content.
    Returns:
        list: List of filtered <tbody> or <table> elements containing job postings.
    """
    # List to store job-related elements
    job_postings = []

    # Track already processed ancestors to avoid duplicates
    seen_ancestors = set()

    # Define job-related labels to look for (case-insensitive)
    job_labels = ["days ago", "just posted", "day ago"]

    # Find all strings in the document matching job-related labels
    matching_strings = soup.find_all(string=lambda text: text and any(label in text.lower() for label in job_labels))

    for match in matching_strings:
        # Find the nearest ancestor that is a <tbody> or <table>
        ancestor = match.find_parent(['tbody', 'table'])

        # Add the ancestor to the results if it hasn't been processed already
        if ancestor and id(ancestor) not in seen_ancestors:
            job_postings.append(ancestor)
            seen_ancestors.add(id(ancestor))  # Use unique ID to track duplicates

    # # If no job postings are found, save the HTML to a log file
    # if not job_postings:
    #     save_flagged_html(soup)

    return job_postings if job_postings else []

# def save_flagged_html(soup):
#     """
#     Save the flagged HTML content to a log file with proper UTC-8 encoding.

#     Args:
#         soup (BeautifulSoup): Parsed HTML content.
#     """
#     # Create the log directory if it doesn't exist
#     log_dir = "./log/flaged_html_files"
#     os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists

#     # Generate a timestamped filename
#     timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
#     file_name = f"flagged_{timestamp}.html"
#     file_path = os.path.join(log_dir, file_name)

#     # Write the HTML content to the file with UTF-8 encoding
#     with open(file_path, "w", encoding="utf-8") as file:
#         file.write(str(soup))

#     print(f"No job postings found. HTML content saved to {file_path}")
