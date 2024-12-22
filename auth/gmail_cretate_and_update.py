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
import scraping.overall_scrap

# Configure logging
logging.basicConfig(level=logging.INFO)

#  Parent: Fetch and process emails
def fetch_and_process_emails(service, senders, success_label_id, failure_label_id, error_recipient):
    """
    Fetches emails from Gmail based on senders and processes them.
    """
    # Combine sender queries into a single query string
    query = f"({' OR '.join([f'from:{sender}' for sender in senders])}) is:unread"
    results = retry_api_call(lambda: service.users().messages().list(userId='me', q=query).execute())
    messages = results.get('messages', [])

    if not messages:
        logging.info("No new emails found.")
        return

    for email in messages:
        process_individual_email(service, email, success_label_id, failure_label_id, error_recipient)

# Child function: Process individual email
def process_individual_email(service, email, success_label_id, failure_label_id, error_recipient):
    """
    Processes a single email.
    - Fetches email details.
    - Extracts content, subject, and sender.
    - Saves email as an HTML file.
    - Marks email as read and adds/removes labels based on success.
    """
    try:
        # Fetch email details
        msg = retry_api_call(lambda: service.users().messages().get(userId='me', id=email['id']).execute())
        payload = msg['payload']
        headers = payload['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
        parts = payload.get('parts', [])

        # Extract email content
        html_content = extract_email_content(parts)

        # Extract received date and sender email
        received_date = next((header['value'] for header in headers if header['name'] == 'Date'), None)
        if not received_date:
            raise Exception("No received date found in email headers.")
        received_datetime = parsedate_to_datetime(received_date)

        sender_email = next((header['value'] for header in headers if header['name'] == 'From'), None)
        if not sender_email:
            raise Exception("No sender email found in email headers.")

        # Save email as an HTML file
        save_email_html(html_content, subject, received_datetime, sender_email)

        # Process email content 
        # For: 
        # All Scraping Steps 
        soup = BeautifulSoup(html_content.encode('utf-8', 'replace'), 'html.parser')
        scraping.overall_scrap.scrap_process_email_content_to_csv(soup)

        # Mark email as read and add success label
        mark_email_processed(service, email['id'], success_label_id, failure_label_id, msg.get('labelIds', []))

        logging.info(f"Successfully processed email: {subject}")

    except Exception as error:
        handle_email_processing_error(service, email, subject, error_recipient, failure_label_id, error)

# Helper function: Extract email content
def extract_email_content(parts):
    """
    Extracts HTML or plain text content from email parts.
    """
    for part in parts:
        if part['mimeType'] == 'text/html':
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif part['mimeType'] == 'text/plain':
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    raise Exception("No HTML or plain text content found in email.")

# Helper function: Mark email as processed
def mark_email_processed(service, email_id, success_label_id, failure_label_id, email_labels):
    """
    Marks email as read and adds/removes appropriate labels.
    """
    retry_api_call(lambda: service.users().messages().modify(
        userId='me',
        id=email_id,
        body={"removeLabelIds": ["UNREAD"], "addLabelIds": [success_label_id]}
    ).execute())

    if failure_label_id in email_labels:
        retry_api_call(lambda: service.users().messages().modify(
            userId='me',
            id=email_id,
            body={"removeLabelIds": [failure_label_id]}
        ).execute())

# Helper function: Handle email processing error
def handle_email_processing_error(service, email, subject, error_recipient, failure_label_id, error):
    """
    Handles errors during email processing.
    - Logs error.
    - Labels email as a failure.
    - Sends an error notification email.
    """
    error_message = f"""
    Failed to process email with ID: {email['id']}
    Subject: {subject}
    Error: {error}
    """
    logging.error(error_message)

    retry_api_call(lambda: service.users().messages().modify(
        userId='me',
        id=email['id'],
        body={"addLabelIds": [failure_label_id]}
    ).execute())

    send_error_email(service, error_recipient, f"Job Scraping Error: {error}", error_message)

# Supporting function: Retry API call
def retry_api_call(call, retries=3, delay=2):
    """
    Retries an API call with exponential backoff.
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

# Supporting function: Ensure label exists
def ensure_label_exists(service, label_name):
    """
    Ensures a Gmail label exists and returns its ID.
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
        logging.error(f"Error ensuring label exists: {error}")
        return None

# Supporting function: Send error notification email
def send_error_email(service, recipient, subject, error_message):
    """
    Sends an email to notify about a processing error.
    """
    try:
        message = {
            "raw": base64.urlsafe_b64encode(
                f"To: {recipient}\r\nSubject: {subject}\r\n\r\n{error_message}".encode("utf-8")
            ).decode("utf-8")
        }
        service.users().messages().send(userId='me', body=message).execute()
        logging.info(f"Error notification sent to {recipient}")
    except HttpError as error:
        logging.error(f"Failed to send error notification: {error}")

# Supporting function: Save email as HTML file
def save_email_html(content, title, received_datetime, sender_email):
    """
    Saves email content as an HTML file under a structured folder hierarchy.
    """
    try:
        # Extract sender details
        extracted_email = next((part.strip("<>") for part in sender_email.split() if "@" in part and "." in part), None)
        if not extracted_email:
            raise ValueError(f"Invalid sender email: {sender_email}")

        sender_name = sender_email.split("<")[0].strip() if "<" in sender_email else "Unknown Sender"
        safe_sender_name = "_".join(sender_name.split())
        sender_folder_name = f"{safe_sender_name}___{extracted_email}"

        # Define folder structure
        folder_path = os.path.join(
            "data",
            sender_folder_name,
            str(received_datetime.year),
            received_datetime.strftime("%B"),
            f"{received_datetime.day:02d}"
        )
        os.makedirs(folder_path, exist_ok=True)

        # Create file name
        date_part = received_datetime.strftime("%Y_%B_%d")
        time_part = received_datetime.strftime("Time_%H_%M_%S_%f")[:-3]
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()
        file_name = f"{date_part}___{time_part}___Title_{safe_title}.html"

        # Save file
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        update_log("success", f"Email saved: {title}, Path: {file_path}")

    except Exception as e:
        update_log("failure", f"Failed to save email: {title}, Error: {e}")
        raise

# Supporting function: Update log files
def update_log(log_type, message):
    """
    Updates log files for email processing operations.
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
