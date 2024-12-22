import os
import logging
from datetime import datetime
import pytz
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
import scraping.overall_scrap
import scraping.scrap_job_blocks
import scraping.scrap_job_elements
from collections import deque
import logging

logging.basicConfig(level=logging.error)

# logging.info("This is an info message.")
# logging.error("This is an error message.")


def process_emails_with_transaction(service, senders, error_recipient):
    """
    Process emails from specific senders. Implements fetching, scraping, and final updates.
    """
    try:
        # Ensure necessary labels exist
        labels = {
            "success_fetched": ensure_label_exists(service, "email fetched successfully"),
            "failure_fetched": ensure_label_exists(service, "failed fetching"),
            "success_scraped": ensure_label_exists(service, "successfully scraped"),
            "failure_scraped": ensure_label_exists(service, "failed scraping"),
            "success_final": ensure_label_exists(service, "success"),
            "failure_final": ensure_label_exists(service, "failure")
        }
        
        if not all(labels.values()):
            logging.error("Failed to ensure all required labels.")
            return

        # Combine sender queries into a single query string
        query = f"({' OR '.join([f'from:{sender}' for sender in senders])}) is:unread"
        results = retry_api_call(lambda: service.users().messages().list(userId='me', q=query).execute())
        messages = results.get('messages', [])

        if not messages:
            logging.info("No new emails found.")
            return

        for email in messages:
            email_id = email.get('id')
            try:
                # Step 1: Fetching Email
                email_data = fetch_email(service, email_id)
                html_content, metadata = email_data["html_content"], email_data["metadata"]

                # Step 2: Scraping Steps
                scrape_email_content(html_content, metadata, labels, service, email_id)

                # Step 3: Final Updates on Success
                finalize_email(email_id, service, html_content, metadata, labels, error_recipient, success=True)

            except Exception as e:
                # Step 3: Final Updates on Failure
                logging.error(f"Email processing failed for ID {email_id}: {e}")
                finalize_email(email_id, service, html_content, metadata, labels, error_recipient, success=False, error=e)

    except HttpError as error:
        logging.error(f"An API error occurred: {error}")


def fetch_email(service, email_id):
    """
    Fetch email content, decode HTML, and extract metadata.
    """
    try:
        msg = retry_api_call(lambda: service.users().messages().get(userId='me', id=email_id).execute())
        payload = msg['payload']
        headers = payload['headers']

        # Extract metadata
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")
        sender_email = next((header['value'] for header in headers if header['name'] == 'From'), None)
        received_date = next((header['value'] for header in headers if header['name'] == 'Date'), None)

        if not received_date:
            raise Exception("No received date found in email headers.")
        received_datetime = parsedate_to_datetime(received_date)

        # Extract HTML content
        parts = payload.get('parts', [])
        html_content = None
        for part in parts:
            if part['mimeType'] == 'text/html':
                html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
        if not html_content:
            raise Exception("No HTML content found in email.")

        logging.info(f"Email fetched successfully: Subject: {subject}, Sender: {sender_email}")
        return {"html_content": html_content, "metadata": {"subject": subject, "sender_email": sender_email, "received_datetime": received_datetime}}

    except Exception as e:
        logging.error(f"Failed to fetch email with ID {email_id}: {e}")
        raise


def scrape_email_content(html_content, metadata, labels, service, email_id):
    """
    Scrape the email's HTML content and save extracted data.
    """
    try:
        soup = BeautifulSoup(html_content.encode('utf-8', 'replace'), 'html.parser')
        scraping.overall_scrap.scrap_process_email_content_to_csv(soup)
        logging.info(f"Scraping successful for email: {metadata['subject']}")
    except Exception as e:
        logging.error(f"Scraping failed for email {metadata['subject']} (ID: {email_id}): {e}")
        raise


def finalize_email(email_id, service, html_content, metadata, labels,error_recipient, success, error=None):
    """
    Handle final updates on email based on success or failure.
    """
    try:
        if success:
            # Save email HTML to structured folder
            save_email_html(html_content, metadata['subject'], metadata['received_datetime'], metadata['sender_email'])

            # Remove unread label
            mark_email_as_read(service,email_id)
            

            # Add success labels and remove failure labels
            retry_api_call(lambda: service.users().messages().modify(
                userId='me',
                id=email_id,
                body={"addLabelIds": [labels['success_final']], "removeLabelIds": [labels['failure_final']]}
            ).execute())
            logging.info(f"Email processed successfully: {metadata['subject']}")

        else:
            # Save failed HTML content to `failed_emails` directory
            save_failed_html(html_content, metadata['subject'], metadata['received_datetime'], metadata['sender_email'])

            # send_error_email(service, recipient, subject, error_message)
            send_error_email(service, error_recipient, metadata['subject'], "Error")
            
            # Remove unread label
            mark_email_as_read(service,email_id)
            
            # Add failure labels and log error
            retry_api_call(lambda: service.users().messages().modify(
                userId='me',
                id=email_id,
                body={"addLabelIds": [labels['failure_final']]}
            ).execute())
            logging.error(f"Email processing failed for {metadata['subject']}: {error}")

    except Exception as e:
        logging.error(f"Finalizing email failed: {e}")

def save_failed_html(content, title, received_datetime, sender_email):
    """
    Save failed email content to a structured `failed_emails` directory.
    The directory name will be structured as `sender_name___sender_email`.
    """
    try:
        # Step 2: Extract and sanitize the sender's name
        sender_name = sender_email.split("<")[0].strip() if "<" in sender_email else "Unknown Sender"
        safe_sender_name = "_".join(sender_name.split())  # Replace spaces with underscores

        # Sanitize sender_email to remove invalid characters
        safe_sender_email = "".join(c for c in sender_email if c.isalnum() or c in "._-@")
        safe_sender_email = safe_sender_email.replace("<", "").replace(">", "")  # Remove remaining invalid characters

        # Create a folder name using sender_name and sanitized sender_email
        folder_name = f"{safe_sender_name}___{safe_sender_email}"
        folder_path = os.path.join("data", "failed_emails", folder_name)

        # Debug: Print the folder path for verification
        print(f"Debug - Folder path: {folder_path}")

        # Create the directory if it does not exist
        os.makedirs(folder_path, exist_ok=True)

        # Format the date and time parts for the filename
        date_part = received_datetime.strftime("%Y_%B_%d")
        time_part = received_datetime.strftime("Time_%H_%M_%S")

        # Create a safe title for the file
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()

        # Create the full file name
        file_name = f"{date_part}___{time_part}___Title_{safe_title}.html"
        file_path = os.path.join(folder_path, file_name)

        # Debug: Print the file path for verification
        print(f"Debug - File path: {file_path}")

        # Write the content to the file
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        logging.info(f"Failed email saved to {file_path}")
    except Exception as e:
        if hasattr(e, 'winerror') and e.winerror == 123:
            logging.warning(f"Sanitized path flagged as invalid: {folder_path}")
        else:
            logging.error(f"Failed to save email content: {e}")


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
    """
    try:
        # Step 1: Extract the email address from the sender
        extracted_email = None
        for part in sender_email.split():
            if "@" in part and "." in part:
                extracted_email = part.strip("<>")  # Remove surrounding brackets
                break

        if not extracted_email:
            raise ValueError(f"Invalid sender email: {sender_email}")

        # Step 2: Extract and sanitize the sender's name
        sender_name = sender_email.split("<")[0].strip() if "<" in sender_email else "Unknown Sender"
        safe_sender_name = "_".join(sender_name.split())  # Replace spaces with underscores

        # Step 3: Create the parent folder name
        sender_folder_name = f"{safe_sender_name}___{extracted_email}"

        # Step 4: Define the folder structure
        folder_path = os.path.join(
            "data",
            sender_folder_name,
            str(received_datetime.year),
            received_datetime.strftime("%B"),
            f"{received_datetime.day:02d}"
        )
        os.makedirs(folder_path, exist_ok=True)

        # Step 5: Format the file name
        date_part = received_datetime.strftime("%Y_%B_%d")
        time_part = received_datetime.strftime("Time_%H_%M_%S_%f")[:-3]  # Truncated milliseconds
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()  # Limit to 30 chars
        file_name = f"{date_part}___{time_part}___Title_{safe_title}.html"

        # Step 6: Save the HTML content
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        # Step 7: Log the success
        log_message = f"Successfully saved email: '{title}' to '{file_path}'."
        logging.info(log_message)  # Use centralized logging
        print(f"Email saved to {file_path}")

    except Exception as e:
        # Step 8: Log the failure
        log_message = f"Failed to save email: '{title}'. Error: {e}"
        logging.error(log_message)  # Use centralized logging
        raise



def retry_api_call(call, retries=3, delay=2):
    for i in range(retries):
        try:
            return call()
        except HttpError as e:
            if i < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise e


def ensure_label_exists(service, label_name):
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
        logging.error(f"Failed to create label {label_name}: {error}")
        return None

def mark_email_as_read(service, email_id):
    """
    Marks a specific Gmail message as read.

    Parameters:
        email_id (str): The ID of the email to mark as read.

    Returns:
        bool: True if the email was successfully marked as read, False otherwise.
    """

    try:
        # Mark the message as read
        service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

        print(f"Email with ID {email_id} marked as read.")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

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

# import os
# import logging
# from datetime import datetime
# import pytz

# def configure_logging():
#     """
#     Configures logging to write logs to both console and log files (daily and monthly).
#     Ensures log folders and files are created if they do not exist.
#     """
#     tz = pytz.timezone('America/Toronto')
#     current_time = datetime.now(tz)

#     # Define log folder paths
#     monthly_log_folder = os.path.join("logs", "monthly")
#     daily_log_folder = os.path.join("logs", "daily")

#     # Ensure log directories exist
#     os.makedirs(monthly_log_folder, exist_ok=True)
#     os.makedirs(daily_log_folder, exist_ok=True)

#     # Define log file paths
#     monthly_log_file = os.path.join(
#         monthly_log_folder,
#         f"{current_time.strftime('%Y_%B')}_log.txt"
#     )
#     daily_log_file = os.path.join(
#         daily_log_folder,
#         f"{current_time.strftime('%Y_%B_%d')}_log.txt"
#     )

#     # Ensure log files exist
#     if not os.path.exists(monthly_log_file):
#         with open(monthly_log_file, 'w', encoding='utf-8') as f:
#             f.write("Monthly Log Initialized\n")

#     if not os.path.exists(daily_log_file):
#         with open(daily_log_file, 'w', encoding='utf-8') as f:
#             f.write("Daily Log Initialized\n")

#     # Configure the root logger
#     logger = logging.getLogger()
#     logger.setLevel(logging.INFO)

#     # Console handler
#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(logging.INFO)
#     console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

#     # Daily file handler
#     daily_handler = logging.FileHandler(daily_log_file)
#     daily_handler.setLevel(logging.INFO)
#     daily_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

#     # Monthly file handler
#     monthly_handler = logging.FileHandler(monthly_log_file)
#     monthly_handler.setLevel(logging.INFO)
#     monthly_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

#     # Add handlers to logger
#     logger.addHandler(console_handler)
#     logger.addHandler(daily_handler)
#     logger.addHandler(monthly_handler)

#     logging.info("Logging configured successfully.")
