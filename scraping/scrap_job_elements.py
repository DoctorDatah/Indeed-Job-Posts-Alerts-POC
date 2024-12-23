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
import re

logging.basicConfig(level=logging.INFO)

def get_individual_job(soup):
    """
    Extract job details from the given BeautifulSoup object, handling potential HTML structure variations.

    Args:
        soup (BeautifulSoup): Parsed BeautifulSoup object of the page.

    Returns:
        pd.DataFrame: A DataFrame containing job details.
    """
    # Prepare DataFrame from <tr> elements
    rows = soup.find_all('tr')
##    logging.info(f"Found {len(rows)} <tr> elements.")

    data = []
    for idx, row in enumerate(rows, start=1):  # Start numbering at 1
        # Extract text content and links from the row
        columns = [td.text.strip() for td in row.find_all('td')]
        link = row.find('a', href=True)  # Find the first <a> tag with href attribute
        row_data = {
            "Number": idx,
            "TR HTML": str(row),
            "Link": link['href'] if link else None,  # Add the link if present
        }
        # Dynamically add data columns
        for i, col in enumerate(columns, start=1):
            row_data[f"Data {i}"] = col
        data.append(row_data)

    tr_df = pd.DataFrame(data)

    # Process the DataFrame based on the specified logic
    job_data = {
        "title": None,
        "link": None,
        "company": None,
        "rating": None,
        "location": None,
        "type": None,
        "description": None,
        "days_posted": None,
        "days": None
    }

    for _, row in tr_df.iterrows():
        number = row['Number']

        # Assign values based on the row number logic
        if number == 1:
            job_data['title'] = row.get('Data 1', None)
            job_data['link'] = row.get('Link', None)
        elif number == 3:
            job_data['company'] = row.get('Data 1', None)
            job_data['rating'] = row.get('Data 2', None)
        elif number == 4:
            location_text = row.get('Data 1', None)
            if location_text and '•' in location_text:
                location_parts = location_text.split('•')
                job_data['location'] = location_parts[0].strip()
                job_data['type'] = location_parts[1].strip()
            else:
                job_data['location'] = location_text
                job_data['type'] = None
        elif number == len(tr_df):
            job_data['days_posted'] = row.get('Data 1', None)
        elif number == len(tr_df) - 1:
            job_data['description'] = row.get('Data 1', None)

    # Add posting_date, fetched_date, and calculate days
    current_date = datetime.now()
    days_posted_text = job_data['days_posted']

    if days_posted_text:
        if "day" in days_posted_text.lower():
            # Extract numeric value of days
            days_ago = int(''.join(filter(str.isdigit, days_posted_text))) if any(c.isdigit() for c in days_posted_text) else 1
            posting_date = current_date - timedelta(days=days_ago)
            job_data['days'] = days_ago
        elif "just posted" in days_posted_text.lower():
            posting_date = current_date
            job_data['days'] = 0
        else:
            posting_date = current_date
            job_data['days'] = None
    else:
        posting_date = None
        job_data['days'] = None

    job_data['posting_date'] = posting_date.strftime('%Y-%m-%d') if posting_date else None
    job_data['fetched_date'] = current_date.strftime('%Y-%m-%d')

    # Convert job_data to DataFrame
    job_df = pd.DataFrame([job_data])

    # Print final individual DataFrame
 #   print(job_df)

    return job_df
