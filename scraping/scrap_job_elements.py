import pandas as pd
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import logging
import scraping.scrap_job_blocks
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)


def get_individual_job(soup):
    """
    Dynamically scrape job title, link, location, and days posted from the job HTML.
    Args:
        soup (BeautifulSoup): Parsed BeautifulSoup object of the job's HTML.
    Returns:
        pd.DataFrame: A DataFrame containing the job title, link, location, days posted, posting date, and fetched date.
    """
    job_data = {"title": [], "link": [], "location": [], "days_posted": [], "posting_date": [], "fetched_date": []}

    # Identify potential links for the title
    link_tags = soup.find_all('a', href=True)
    rating_tag = None

    # Dynamically locate the rating
    for tag in soup.find_all():
        if tag.name == "td" and tag.find("img", alt=True) and "rating" in tag.img['alt'].lower():
            rating_tag = tag
            break

    # Ensure the title link comes before the rating tag
    if rating_tag:
        for link in link_tags:
            if link and link.find_next() == rating_tag.find_parent():  # Check relative position
                job_data['title'].append(link.text.strip())
                job_data['link'].append(link['href'])  # Capture the link URL
                break

    # Dynamically find the location (text following the rating)
    if rating_tag:
        location_tag = rating_tag.find_next(string=True)
        if location_tag:
            job_data['location'].append(location_tag.strip())
        else:
            job_data['location'].append(None)

    # Dynamically find the days posted
    date_labels = ["days ago", "day ago", "just posted"]
    days_posted_found = False
    for tag in soup.find_all(string=True):
        if any(label in tag.lower() for label in date_labels):
            job_data['days_posted'].append(tag.strip())
            days_posted_found = True
            break

    if not days_posted_found:
        job_data['days_posted'].append(None)

    # Calculate the posting date and fetched date
    current_date = datetime.now()
    for days_posted in job_data['days_posted']:
        if days_posted:
            if "just posted" in days_posted.lower():
                posting_date = current_date
            elif "day ago" in days_posted.lower() or "days ago" in days_posted.lower():
                days = int(''.join(filter(str.isdigit, days_posted)))
                posting_date = current_date - timedelta(days=days)
            else:
                posting_date = None
        else:
            posting_date = None

        job_data['posting_date'].append(posting_date.strftime('%Y-%m-%d') if posting_date else None)

        # Add fetched date as the current date
        job_data['fetched_date'].append(current_date.strftime('%Y-%m-%d'))

    # Convert the data dictionary to a DataFrame
    job_df = pd.DataFrame(job_data)

    return job_df



