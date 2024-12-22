import pandas as pd
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import logging
import scraping.scrap_job_blocks
import scraping.scrap_job_elements

logging.basicConfig(level=logging.INFO)


from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup



# All steps togther.
def scrap_process_email_content_to_csv(soup):
    """Process email content through scraping and data extraction."""
    try:
        # Step 2: Extract individual job blocks as a list of soups
        job_blocks = scraping.scrap_job_blocks.extract_individual_job_blocks(soup)

        # Step 3: Scrape all indiviual job details into a DataFrame
        jobs_df = scrap_all_individual_jobs(job_blocks)

        # Step 4: append the DataFrame to a CSV file
        results_create_or_append_to_csv(jobs_df, reset_file=False)

        logging.info("Successfully processed email content for job data.")
    except Exception as e:
        logging.error(f"Failed to process email content: {e}")
        raise



############################################################################################
def scrap_all_individual_jobs(soup_list):
    """
    Takes a list of soup objects and applies scraping.scrap_job_elements.get_data on each.
    Returns a unified DataFrame.
    """
    all_jobs = []
    for soup in soup_list:
        job_data = scraping.scrap_job_elements.get_individual_job(soup)
        all_jobs.append(job_data)

    # Concatenate all DataFrames into one
    unified_dataframe = pd.concat(all_jobs, ignore_index=True)
    return unified_dataframe



def results_create_or_append_to_csv(dataframe, reset_file=False):
    """
    Appends a DataFrame to a CSV file named with the current year and month.
    The file is stored in ./data/raw_processed. If the file does not exist, it is created.

    Args:
        dataframe (pd.DataFrame): The DataFrame to append to the CSV file.
        reset_file (bool): If True, resets the file and writes the DataFrame as a fresh file.
    """
    # Ensure the directory exists
    directory = './data/raw_processed'
    os.makedirs(directory, exist_ok=True)

    # Generate the filename based on the current year and month
    current_year_month = datetime.now().strftime('%Y_%m')
    file_path = os.path.join(directory, f'{current_year_month}.csv')

    # Handle file writing based on the reset_file parameter
    if reset_file or not os.path.exists(file_path):
        dataframe.to_csv(file_path, mode='w', header=True, index=False)
        print(f"Data written to {file_path} as a fresh file.")
    else:
        dataframe.to_csv(file_path, mode='a', header=False, index=False)
        print(f"Data appended to {file_path}.")

