# Import required libraries
from bs4 import BeautifulSoup
import requests
import os
import base64
import webbrowser
from tempfile import NamedTemporaryFile

import os
from bs4 import BeautifulSoup

# Step 1: Parse local HTML file
def parse_local_html(file_path):
    """Parse a local HTML file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    print("Local HTML file parsed successfully.")
    return soup


# Example usage for local file
# local_html_path = "path/to/your/local_file.html"
# local_soup = parse_local_html(local_html_path)



##############################################################
# Testing and dev fucntion only

def fetch_email_html_content_most_recent_only(service):
    """Fetch the top email from <alert@indeed.com> and return its HTML content as a BeautifulSoup object."""
    try:
        # Search query to find emails from <alert@indeed.com>
        query = "from:alert@indeed.com"
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()

        messages = results.get('messages', [])

        if not messages:
            print("No emails found from <alert@indeed.com>.")
            return None

        # Fetch the top email
        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()

        # Extract email body
        payload = message['payload']
        parts = payload.get('parts', [])

        email_body = None

        # Iterate through parts to find text/html
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/html' and 'body' in part and 'data' in part['body']:
                email_body = decode_email_body(part['body']['data'])
                break

        if not email_body:
            print("No HTML body found in the email.")
            return None

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(email_body, 'html.parser')

        print("Email HTML content fetched and parsed successfully.")
        return soup

    except Exception as e:
        print("An error occurred while fetching the email:", e)
        return None


##############################################################



def render_html(block):
    """
    Renders a BeautifulSoup object or raw HTML string into a structured, indented HTML format.
    Args:
        block (BeautifulSoup or str): The HTML block to render.
    Returns:
        str: Pretty-printed HTML content.
    """
    if not block:
        return "No HTML content to render."
    
    # If the input is a BeautifulSoup object, prettify it
    if hasattr(block, 'prettify'):
        return block.prettify()

    # If it's already a string, parse and prettify it
    try:
        soup = BeautifulSoup(block, 'html.parser')
        return soup.prettify()
    except Exception as e:
        return f"Error rendering HTML: {e}"



##############################################################


def open_html_in_browser(html_content):
    """
    Open a given HTML content in the default web browser for validation.
    
    Args:
        html_content (str): The HTML content to display in the browser.
    """
    # Create a temporary HTML file
    with NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8') as temp_file:
        temp_file.write(html_content)
        temp_file_path = temp_file.name

    # Open the file in the default web browser
    webbrowser.open(f"file://{os.path.abspath(temp_file_path)}")


##############################################################


def fetch_email_and_save_as_html(service):
    """Fetch the top email from <alert@indeed.com> and save it as an HTML file."""
    try:
        # Search query to find emails from <alert@indeed.com>
        query = "from:alert@indeed.com"
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()

        messages = results.get('messages', [])

        if not messages:
            print("No emails found from <alert@indeed.com>.")
            return

        # Fetch the top email
        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()

        # Extract email body
        payload = message['payload']
        parts = payload.get('parts', [])

        email_body = None

        # Iterate through parts to find text/html
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/html' and 'body' in part and 'data' in part['body']:
                email_body = decode_email_body(part['body']['data'])
                break

        if not email_body:
            print("No HTML body found in the email.")
            return

        # Save the email body as an HTML file
        filename = "src/usecase_most_recent/indeed_alert.html"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(email_body)
        print(f"Email saved as {filename}. Open this file in a browser to examine it.")

    except Exception as e:
        print("An error occurred while fetching the email:", e)



        
########################################################################################
# helper funciton(s) 
########################################################################################
def decode_email_body(encoded_body):
    """Decode base64 encoded email body."""
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_body)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        print("Error decoding email body:", e)
        return "Error decoding body."



######################################################################################## 
    