import threading
import time
import processing.latest_emails 
import auth.gmail_auth
import atexit
import signal



# Global variable to control the fetching process
is_fetching = False
fetch_thread = None



def start_email_fetch(service, senders, error_recipient, interval=10):
    """
    Start continuously fetching new emails at the specified interval.

    Args:
        service: The Gmail API service instance.
        senders (list): List of sender email addresses to filter emails from.
        error_recipient (str): Email address to notify in case of processing errors.
        interval (int): Time interval (in seconds) between email fetch attempts.
    """
    global is_fetching, fetch_thread

    # Refreshing Gmail auth
    service = auth.gmail_auth.authenticate_gmail()

    if is_fetching:
        print("Email fetching is already running.")
        return

    is_fetching = True

    def fetch_emails():
        """Function to continuously fetch emails."""
        try:
            while is_fetching:
                try:
                    processing.latest_emails.process_emails_with_transaction(
                        service, senders, error_recipient
                    )
                    print("Waiting for new emails...")
                except Exception as e:
                    print(f"Error while fetching emails: {e}")
                time.sleep(interval)
        except Exception as e:
            print(f"Error in email fetching thread: {e}")
        finally:
            stop_email_fetch(service, error_recipient)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop sends SIGTERM
    signal.signal(signal.SIGINT, signal_handler)   # Handle manual interrupt (Ctrl+C)

    # Start the fetching process in a separate thread
    fetch_thread = threading.Thread(target=fetch_emails, daemon=True)
    fetch_thread.start()
    print("Email fetching started.")


def signal_handler(signum, frame):
    print(f"Signal {signum} received. Cleaning up...")
    stop_email_fetch(service, error_recipient)

 


def stop_email_fetch(service, user_email):
    """
    Stop the email fetching process and send a notification email.

    :param service: Authenticated Gmail service object.
    :param user_email: Recipient's email address to send the notification.
    """
    global is_fetching, fetch_thread

    if not is_fetching:
        print("Email fetching is not running.")
        return

    is_fetching = False

    if fetch_thread:
        fetch_thread.join()
        fetch_thread = None

    print("Email fetching stopped.")

    # Send notification email
    send_email(
        service=service,
        to_email=user_email,
        subject="Scraper Stopped",
        body="The email scraper has been stopped."
    )


def send_email(service, to_email, subject, body):
    """
    Sends an email using the Gmail API.

    :param service: Authenticated Gmail service object.
    :param to_email: Recipient's email address.
    :param subject: Email subject.
    :param body: Email body.
    """
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    try:
        service.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        print(f"Notification email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send notification email: {e}")