import os 
import scraping.scrap_job_blocks
import scraping.scrap_job_elements
import processing.latest_emails
import scraping.overall_scrap
import listener.gmail_listener
import processing.logs
from datetime import datetime
import threading
import time
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import os
import subprocess
import auth.gmail_auth
import utils.html_module 
import processing.latest_emails 
import scraping.scrap_job_blocks
import scraping.scrap_job_elements
import scraping.overall_scrap
import listener.gmail_listener


SEARCH_SENDERS = ["malikhqtech@gmail.com", "alert@indeed.com", "noreply@example.com"] 
LABEL_NAME_SUCCESS = "fetched_by_app"
LABEL_NAME_FAILURE = "fetch_failed_for_job_app"
ERROR_NOTIFICATION_EMAIL = "malikhqtech@gmail.com"
# is_fetching = False
# fetch_thread = None



if __name__ == "__main__":
    try:
        service = auth.gmail_auth.authenticate_gmail()
        print("Gmail API authenticated successfully!")
    except Exception as e:
        print("Error during authentication:", e)
            
        
    listener.gmail_listener.start_email_fetch(service, SEARCH_SENDERS, ERROR_NOTIFICATION_EMAIL, interval=10)