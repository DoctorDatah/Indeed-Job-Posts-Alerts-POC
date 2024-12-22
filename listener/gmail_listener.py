import threading
import time
import processing.latest_emails 
import auth.gmail_auth



# Global variable to control the fetching process
is_fetching = False
fetch_thread = None

def start_email_fetch(service, senders, error_recipient, interval=10):
    """
    Start continuously fetching new emails at the specified interval.

    Args:
        service: The Gmail API service instance.
        senders (list): List of sender email addresses to filter emails from.
        success_label (str): Label name for successfully processed emails.
        failure_label (str): Label name for failed emails.
        error_recipient (str): Email address to notify in case of processing errors.
        interval (int): Time interval (in seconds) between email fetch attempts.
    """
    global is_fetching, fetch_thread

    # refreching gmail auth
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

    # Start the fetching process in a separate thread
    fetch_thread = threading.Thread(target=fetch_emails, daemon=True)
    fetch_thread.start()
    print("Email fetching started.")


def stop_email_fetch():
    """
    Stop the email fetching process.
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
