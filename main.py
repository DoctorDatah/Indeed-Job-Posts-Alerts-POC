import os 
import auth.gmail_auth
import utils.html_module 
import scraping.scrap_job_blocks
import scraping.scrap_job_elements
import processing.latest_emails
import scraping.overall_scrap
import listener.gmail_listener
import processing.logs
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
from tkinter.scrolledtext import ScrolledText  # Import ScrolledText for better log display
import threading
import time
from bs4 import BeautifulSoup
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
import threading
import os
import subprocess

SEARCH_SENDERS = ["malikhqtech@gmail.com", "alert@indeed.com", "noreply@example.com"] 
LABEL_NAME_SUCCESS = "fetched_by_app"
LABEL_NAME_FAILURE = "fetch_failed_for_job_app"
ERROR_NOTIFICATION_EMAIL = "malikhqtech@gmail.com"
is_fetching = False
fetch_thread = None

