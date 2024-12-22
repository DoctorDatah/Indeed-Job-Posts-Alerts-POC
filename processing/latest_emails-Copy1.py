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
# from data_prep import extract_job_blocks, process_job_data, save_to_table


# SEARCH_SENDERS = ["malikhq27@gmail.com", "alert@indeed.com", "noreply@example.com"]
# LABEL_NAME_SUCCESS = "fetched_by_app"
# LABEL_NAME_FAILURE = "fetch_failed_or_job_app"
# ERROR_NOTIFICATION_EMAIL = "error_recipient@example.com"
# Configure logging
logging.basicConfig(level=logging.INFO)


def process_emails_with_transaction(service, senders, success_label, failure_label, error_recipient):
    """
    Process emails from specific senders as a transaction. For each email:
    - Fetch the email.
    - Decode and save it as an HTML file.
    - Mark it as read.
    - Add success or failure labels.
    - Remove failure label if the transaction is successful.
    - Send an error email if processing fails.
    """
    try:
        # Ensure success and failure labels exist
        success_label_id = ensure_label_exists(service, success_label)
        failure_label_id = ensure_label_exists(service, failure_label)

        if not success_label_id or not failure_label_id:
            logging.error("Failed to ensure required labels.")
            return

        # Combine sender queries into a single query string
        query = f"({' OR '.join([f'from:{sender}' for sender in senders])}) is:unread"
        results = retry_api_call(lambda: service.users().messages().list(userId='me', q=query).execute())
        messages = results.get('messages', [])

        if not messages:
            logging.info("No new emails found.")
            return

        for email in messages:
            try:
                # Fetch email details
                msg = retry_api_call(lambda: service.users().messages().get(userId='me', id=email['id']).execute())
                payload = msg['payload']
                headers = payload['headers']
                subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
                parts = payload.get('parts', [])

                # Extract email content
                html_content = None
                for part in parts:
                    if part['mimeType'] == 'text/html':
                        html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/plain':  # Fallback for plain text
                        html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                if not html_content:
                    raise Exception("No HTML or plain text content found in email.")

                # Extract received date
                received_date = next((header['value'] for header in headers if header['name'] == 'Date'), None)
                if not received_date:
                    raise Exception("No received date found in email headers.")
                received_datetime = parsedate_to_datetime(received_date)

                # Extract sender email
                sender_email = next((header['value'] for header in headers if header['name'] == 'From'), None)
                if not sender_email:
                    raise Exception("No sender email found in email headers.")

                # Save email as an HTML file
                save_email_html(html_content, subject, received_datetime, sender_email)

                # All Scraping Steps 
                soup = BeautifulSoup(html_content.encode('utf-8', 'replace'), 'html.parser')
                scraping.overall_scrap.scrap_process_email_content_to_csv(soup)
        
                # Mark email as read and add success label
                retry_api_call(lambda: service.users().messages().modify(
                    userId='me',
                    id=email['id'],
                    body={"removeLabelIds": ["UNREAD"], "addLabelIds": [success_label_id]}
                ).execute())

                # Check for failure label and remove it if present
                email_labels = msg.get('labelIds', [])
                if failure_label_id in email_labels:
                    retry_api_call(lambda: service.users().messages().modify(
                        userId='me',
                        id=email['id'],
                        body={"removeLabelIds": [failure_label_id]}
                    ).execute())
                    logging.info(f"Removed failure label from email: {subject}")

                logging.info(f"Successfully processed email: {subject}")

            except Exception as error:
                # Handle failures
                error_message = f"""
                Failed to process email with ID: {email['id']}
                Subject: {subject}
                Sender: {sender_email}
                Received Date: {received_date}
                Error: {error}
                """
                logging.error(error_message)

                # Label the email as a failure
                retry_api_call(lambda: service.users().messages().modify(
                    userId='me',
                    id=email['id'],
                    body={"addLabelIds": [failure_label_id]}
                ).execute())

                # Send error notification email
                send_error_email(service, error_recipient, f"Job Scraping Error: {error}", error_message)

    except HttpError as error:
        logging.error(f"An API error occurred: {error}")



# Helper function to retry API calls with exponential backoff
def retry_api_call(call, retries=3, delay=2):
    for i in range(retries):
        try:
            return call()
        except HttpError as e:
            if i < retries - 1:
                sleep(delay)
                delay *= 2
            else:
                raise e


# Helper Functions
def ensure_label_exists(service, label_name):
    """Ensure the specified label exists in Gmail and return its ID."""
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

def send_error_email(service, recipient, subject, error_message):
    """Send an email to notify about a processing error."""
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


def update_log(log_type, message):
    """
    Updates and maintains logs for email saving operations.
    - Maintains a general monthly log at `/data/log/monthly`.
    - Maintains a daily log at `/data/log/daily`.
    - Prepends new log entries to the beginning of the log file.

    Args:
        log_type (str): Type of log entry ("success" or "failure").
        message (str): The log message to append.

    Logs are structured as:
    - Monthly Logs:
      - File Path: `/data/log/monthly/{Year_Month}_log.txt`
      - Purpose: Consolidates logs (success and failure) for the current month.
    - Daily Logs:
      - File Path: `/data/log/daily/{Year_Month_Day}_log.txt`
      - Purpose: Tracks logs specific to the current day.
    """
    # Set the timezone to Toronto (EST)
    tz = pytz.timezone('America/Toronto')
    current_time = datetime.now(tz)

    # Log folder paths
    monthly_log_folder = os.path.join("data", "log", "monthly")
    daily_log_folder = os.path.join("data", "log", "daily")
    os.makedirs(monthly_log_folder, exist_ok=True)
    os.makedirs(daily_log_folder, exist_ok=True)

    # Monthly log file path
    monthly_log_file = os.path.join(
        monthly_log_folder,
        f"{current_time.strftime('%Y_%B')}_log.txt"
    )

    # Daily log file path
    daily_log_file = os.path.join(
        daily_log_folder,
        f"{current_time.strftime('%Y_%B_%d')}_log.txt"
    )

    # Create log entry with timestamp
    log_entry = f"{current_time.strftime('%Y-%m-%d %H:%M:%S')} [{log_type.upper()}] {message}\n"

    # Helper function to prepend log entry to a file
    def prepend_log(file_path, entry):
        if os.path.exists(file_path):
            # Read the current content
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
        else:
            content = ""
        # Write the new entry followed by the existing content
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(entry + content)

    # Prepend the log entry to the monthly log
    prepend_log(monthly_log_file, log_entry)

    # Prepend the log entry to the daily log
    prepend_log(daily_log_file, log_entry)

    print(f"Log updated: {log_entry.strip()}")


def save_email_html(content, title, received_datetime, sender_email):
    """
    Save email content as an HTML file under a structured folder hierarchy:
    data/sender_name___sender_email/year/month_name/day/YYYY_Month_Day___Time_HH_MM_SS_MS___Title_First_30_Chars.html.

    Args:
        content (str): The HTML content of the email.
        title (str): The title of the email to use as the file name.
        received_datetime (datetime.datetime): The received date and time as a datetime object.
        sender_email (str): The email address of the sender (can include name and brackets).

    Logs:
    - Success logs are recorded when an email is successfully saved.
    - Failure logs are recorded when an error occurs during the save process.

    Examples:
        If the sender's email is "Indeed <alert@indeed.com>", the received date is
        December 19, 2024, 3:03:52 PM, and the email title is "Job Alert - Data Analyst Position Available":

        - Folder structure:
          data/Indeed___alert@indeed.com/2024/December/19/

        - File name:
          2024_December_19___Time_15_03_52_000___Title_Job_Alert_-_Data_Analy.html

        - Full path:
          data/Indeed___alert@indeed.com/2024/December/19/2024_December_19___Time_15_03_52_000___Title_Job_Alert_-_Data_Analy.html
    """


    try:
        # Step 1: Extract the email address from the sender
        # Uses a simple split and checks for '@' and '.' to identify the email part.
        extracted_email = None
        for part in sender_email.split():
            if "@" in part and "." in part:
                extracted_email = part.strip("<>")  # Remove surrounding brackets
                break

        # If no valid email is found, raise an error.
        if not extracted_email:
            raise ValueError(f"Invalid sender email: {sender_email}")

        # Step 2: Extract and sanitize the sender's name
        # The sender name is derived from the text before the '<' character.
        sender_name = sender_email.split("<")[0].strip() if "<" in sender_email else "Unknown Sender"
        safe_sender_name = "_".join(sender_name.split())  # Replace spaces with underscores

        # Step 3: Create the parent folder name
        # Combines the sanitized sender name and email, separated by `___`.
        sender_folder_name = f"{safe_sender_name}___{extracted_email}"

        # Step 4: Define the folder structure
        # Organizes files by year, month, and day based on the email's received date.
        folder_path = os.path.join(
            "data",
            sender_folder_name,
            str(received_datetime.year),
            received_datetime.strftime("%B"),
            f"{received_datetime.day:02d}"
        )
        os.makedirs(folder_path, exist_ok=True)

        # Step 5: Format the file name
        # Includes the date, time (with truncated milliseconds), and sanitized title.
        date_part = received_datetime.strftime("%Y_%B_%d")
        time_part = received_datetime.strftime("Time_%H_%M_%S_%f")[:-3]  # Truncated milliseconds
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()  # Limit to 30 chars
        file_name = f"{date_part}___{time_part}___Title_{safe_title}.html"

        # Step 6: Save the HTML content
        # Opens the file in write mode with UTF-8 encoding and writes the content.
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        # Step 7: Log the success
        # Creates a success message and logs it using the `update_log` function.
        log_message = f"Successfully saved email: {title}, Path: {file_path}"
        update_log("success", log_message)

        print(f"Email saved to {file_path}")

    except Exception as e:
        # Step 8: Log the failure
        # Captures any exceptions, logs the failure, and re-raises the error.
        log_message = f"Failed to save email: {title}, Error: {e}"
        update_log("failure", log_message)
        raise
