import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# Define the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail():
    """Authenticate and get the Gmail API service"""
    creds = None

    # Check if token.pickle already exists for storing user credentials
    if os.path.exists('_secrets/token.pickle'):
        with open('_secrets/token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, ask user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '_secrets/credentials.json', SCOPES
            )
            # Explicitly set redirect_uri for debugging
            flow.redirect_uri = "http://localhost:8080/"
            creds = flow.run_local_server(port=8080)
        # Save credentials for next run
        with open('_secrets/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Build the Gmail API service
    return build('gmail', 'v1', credentials=creds)

def get_account_email(service, user_id='me'):
    """Retrieve the email address of the authenticated Gmail account."""
    try:
        # Get the user's profile information
        profile = service.users().getProfile(userId=user_id).execute()
        email_address = profile.get('emailAddress')
        print("Authenticated Email Address:", email_address)
        return email_address
    except Exception as e:
        print("An error occurred while retrieving the account email:", e)
        return None





