import os
import logging
from datetime import datetime
import pytz
import base64  # Added to handle email encoding
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.utils import parsedate_to_datetime
import re
from bs4 import BeautifulSoup
import scraping.scrap_job_elements

# Configure logging
logging.basicConfig(level=logging.INFO)

# Main entry point function to process emails
def process_emails_with_transaction(service, senders, success_label, failure_label, error_recipient):
    """
    Process emails as a transaction. Handles fetching, saving, marking emails, and managing labels.
    """
    try:
        # Step 1: Ensure necessary labels exist
        success_label_id = ensure_label_exists(service, success_label)
        failure_label_id = ensure_label_exists(service, failure_label)

        if not success_label_id or not failure_label_id:
            logging.error("Failed to ensure required labels.")
            return

        # Step 2: Fetch emails based on sender queries
        query = create_email_query(senders)
        messages = fetch_email_list(service, query)

        if not messages:
            logging.info("No new emails found.")
            return

        # Step 3: Process each email
        for email in messages:
            process_single_email(service, email, success_label_id, failure_label_id, error_recipient)

    except HttpError as error:
        logging.error(f"An API error occurred: {error}")

# Child function: Email fetching query creation
def create_email_query(senders):
    """
    Combine sender queries into a single query string for Gmail API.
    """
    return f"({' OR '.join([f'from:{sender}' for sender in senders])}) is:unread"

# Child function: Fetch email list
def fetch_email_list(service, query):
    """
    Fetch a list of email messages based on the query.
    """
    results = retry_api_call(lambda: service.users().messages().list(userId='me', q=query).execute())
    return results.get('messages', [])

# Child function: Process a single email
def process_single_email(service, email, success_label_id, failure_label_id, error_recipient):
    """
    Process a single email: fetch, save, and label appropriately.
    """
    try:
        # Fetch email details
        msg = fetch_email_details(service, email['id'])

        # Extract content and metadata
        subject, html_content, received_datetime, sender_email = extract_email_data(msg)

        # Save email content
        save_email_html(html_content, subject, received_datetime, sender_email)

        # Perform scraping tasks
        soup = BeautifulSoup(html_content, 'html.parser')
        scraping.scrap_job_elements.process_email_content(soup)

        # Update email labels on successful processing
        update_email_labels(service, email['id'], success_label_id, failure_label_id)

        logging.info(f"Successfully processed email: {subject}")

    except Exception as error:
        handle_email_processing_failure(service, email, subject, sender_email, received_datetime, failure_label_id, error_recipient, error)

# Grandchild function: Fetch email details
def fetch_email_details(service, email_id):
    """
    Fetch the full details of a single email.
    """
    return retry_api_call(lambda: service.users().messages().get(userId='me', id=email_id).execute())

# Grandchild function: Extract email data
def extract_email_data(msg):
    """
    Extract subject, HTML content, received date, and sender email from the email message.
    """
    payload = msg['payload']
    headers = payload['headers']

    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")

    html_content = None
    for part in payload.get('parts', []):
        if part['mimeType'] in ('text/html', 'text/plain'):
            html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            break
    if not html_content:
        raise Exception("No HTML or plain text content found in email.")

    received_date = next((header['value'] for header in headers if header['name'] == 'Date'), None)
    if not received_date:
        raise Exception("No received date found in email headers.")
    received_datetime = parsedate_to_datetime(received_date)

    sender_email = next((header['value'] for header in headers if header['name'] == 'From'), None)
    if not sender_email:
        raise Exception("No sender email found in email headers.")

    return subject, html_content, received_datetime, sender_email

# Grandchild function: Update email labels
def update_email_labels(service, email_id, success_label_id, failure_label_id):
    """
    Mark email as read, add success label, and remove failure label if present.
    """
    retry_api_call(lambda: service.users().messages().modify(
        userId='me',
        id=email_id,
        body={"removeLabelIds": ["UNREAD"], "addLabelIds": [success_label_id]}
    ).execute())

# Grandchild function: Handle email processing failure
def handle_email_processing_failure(service, email, subject, sender_email, received_date, failure_label_id, error_recipient, error):
    """
    Handle failures by logging errors, updating failure label, and sending a notification.
    """
    error_message = f"""
    Failed to process email with ID: {email['id']}
    Subject: {subject}
    Sender: {sender_email}
    Received Date: {received_date}
    Error: {error}
    """
    logging.error(error_message)

    retry_api_call(lambda: service.users().messages().modify(
        userId='me',
        id=email['id'],
        body={"addLabelIds": [failure_label_id]}
    ).execute())

    send_error_email(service, error_recipient, f"Job Scraping Error: {error}", error_message)

# Helper function: Retry API calls with backoff
def retry_api_call(call, retries=3, delay=2):
    """
    Retry API calls with exponential backoff.
    """
    for i in range(retries):
        try:
            return call()
        except HttpError as e:
            if i < retries - 1:
                sleep(delay)
                delay *= 2
            else:
                raise e

# Helper function: Ensure label exists
def ensure_label_exists(service, label_name):
    """
    Ensure the specified label exists in Gmail and return its ID.
    """
    try:
        label_list = service.users().labels().list(userId='me').execute()
        labels = label_list.get('labels', [])
        for label in labels:
            if label['name'] == label_name:
                return label['id']

        label_body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        new_label = service.users().labels().create(userId='me', body=label_body).execute()
        return new_label['id']
    except HttpError as error:
        print(f"An error occurred while ensuring label exists: {error}")
        return None

# Helper function: Send error email
def send_error_email(service, recipient, subject, error_message):
    """
    Send an email to notify about a processing error.
    """
    try:
        message = {
            "raw": base64.urlsafe_b64encode(
                f"To: {recipient}\r\nSubject: {subject}\r\n\r\n{error_message}".encode("utf-8")
            ).decode("utf-8")
        }
        service.users().messages().send(userId='me', body=message).execute()
        print(f"Error notification sent to {recipient}")
    except HttpError as error:
        print(f"Failed to send error notification: {error}")

# Helper function: Update log
def update_log(log_type, message):
    """
    Update and maintain logs for email operations.
    """
    tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(tz)

    monthly_log_folder = os.path.join("data", "log", "monthly")
    daily_log_folder = os.path.join("data", "log", "daily")
    os.makedirs(monthly_log_folder, exist_ok=True)
    os.makedirs(daily_log_folder, exist_ok=True)

    monthly_log_file = os.path.join(
        monthly_log_folder,
        f"{current_time.strftime('%Y_%B')}_log.txt"
    )

    daily_log_file = os.path.join(
        daily_log_folder,
        f"{current_time.strftime('%Y_%B_%d')}_log.txt"
    )

    log_entry = f"{current_time.strftime('%Y-%m-%d %H:%M:%S')} [{log_type.upper()}] {message}\n"

    def prepend_log(file_path, entry):
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
        else:
            content = ""
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(entry + content)

    prepend_log(monthly_log_file, log_entry)
    prepend_log(daily_log_file, log_entry)
    print(f"Log updated: {log_entry.strip()}")

# Helper function: Save email as HTML
def save_email_html(content, title, received_datetime, sender_email):
    """
    Save email content as an HTML file under a structured folder hierarchy.
    """
    try:
        extracted_email = extract_email_address(sender_email)
        sender_folder_name = create_sender_folder_name(sender_email, extracted_email)

        folder_path = create_email_folder_structure(received_datetime, sender_folder_name)

        file_name = create_email_file_name(received_datetime, title)
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        log_message = f"Successfully saved email: {title}, Path: {file_path}"
        update_log("success", log_message)
        print(f"Email saved to {file_path}")

    except Exception as e:
        log_message = f"Failed to save email: {title}, Error: {e}"
        update_log("failure", log_message)
        raise

# Grandchild function: Extract email address
def extract_email_address(sender_email):
    """
    Extract the email address from the sender string.
    """
    for part in sender_email.split():
        if "@" in part and "." in part:
            return part.strip("<>")
    raise ValueError(f"Invalid sender email: {sender_email}")

# Grandchild function: Create sender folder name
def create_sender_folder_name(sender_email, extracted_email):
    """
    Create a folder name combining sender's name and email.
    """
    sender_name = sender_email.split("<")[0].strip() if "<" in sender_email else "Unknown Sender"
    safe_sender_name = "_".join(sender_name.split())
    return f"{safe_sender_name}___{extracted_email}"

# Grandchild function: Create email folder structure
def create_email_folder_structure(received_datetime, sender_folder_name):
    """
    Create folder structure for email storage based on received date.
    """
    folder_path = os.path.join(
        "data",
        sender_folder_name,
        str(received_datetime.year),
        received_datetime.strftime("%B"),
        f"{received_datetime.day:02d}"
    )
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

# Grandchild function: Create email file name
def create_email_file_name(received_datetime, title):
    """
    Create a sanitized file name for the email content.
    """
    date_part = received_datetime.strftime("%Y_%B_%d")
    time_part = received_datetime.strftime("Time_%H_%M_%S_%f")[:-3]
    safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()
    return f"{date_part}___{time_part}___Title_{safe_title}.html"
