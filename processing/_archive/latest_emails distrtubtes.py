import os
import logging
from datetime import datetime
import pytz
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.utils import parsedate_to_datetime
import re
from bs4 import BeautifulSoup
import scraping.scrap_job_elements
import gmail.gmail_cretate_and_update

# Configure logging
logging.basicConfig(level=logging.INFO)

# Entry function for processing emails
def process_emails_with_transaction(service, senders, success_label, failure_label, error_recipient):
    """
    Entry point to process emails as a transaction.
    - Ensures necessary labels exist.
    - Fetches unread emails from specified senders.
    - Decodes and processes email content.
    - Adds success or failure labels based on the outcome.
    """
    try:
        # Ensure labels exist
        success_label_id = gmail.gmail_cretate_and_update.ensure_label_exists(service, success_label)
        failure_label_id = gmail.gmail_cretate_and_update.ensure_label_exists(service, failure_label)

        if not success_label_id or not failure_label_id:
            logging.error("Failed to ensure required labels.")
            return

        # Fetch and process emails
        gmail.gmail_cretate_and_update.fetch_and_process_emails(service, senders, success_label_id, failure_label_id, error_recipient)

    except HttpError as error:
        logging.error(f"An API error occurred: {error}")
