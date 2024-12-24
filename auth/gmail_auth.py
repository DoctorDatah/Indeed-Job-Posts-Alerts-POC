import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Set the scope for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Configure paths
TOKEN_PATH = './_secrets/token.pickle'
CREDENTIALS_PATH = './_secrets/credentials.json'

def ensure_secrets_directory():
    """Ensure the _secrets directory exists"""
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

def load_credentials():
    """Load existing credentials from pickle file"""
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, 'rb') as token:
                return pickle.load(token)
        except Exception as e:
            logging.warning(f"Error loading token file: {e}")
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH)  # Remove corrupted token file
    return None

def save_credentials(creds):
    """Save credentials to pickle file"""
    try:
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        logging.info("Credentials saved successfully")
    except Exception as e:
        logging.error(f"Error saving credentials: {e}")

def authenticate_gmail():
    """
    Authenticate and return the Gmail API service with enhanced error handling
    and token management.
    """
    ensure_secrets_directory()
    
    try:
        # Load existing credentials
        creds = load_credentials()
        
        # Check if we need to refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logging.info("Refreshing access token...")
                    creds.refresh(Request())
                except RefreshError as e:
                    logging.warning(f"Token refresh failed: {e}")
                    creds = None
            
            # If still no valid credentials, start new OAuth flow
            if not creds:
                logging.info("Starting new OAuth flow...")
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"No credentials file found at {CREDENTIALS_PATH}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH,
                    SCOPES,
                    redirect_uri='http://localhost:8080/'
                )
                
                creds = flow.run_local_server(
                    port=8080,
                    access_type='offline',
                    prompt='consent',
                    success_message='Authentication successful! You can close this window.',
                    open_browser=True
                )
                
                # Save the new credentials
                save_credentials(creds)
        
        # Build and return the Gmail service
        service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        
        # Verify the connection by getting user profile
        user_profile = service.users().getProfile(userId='me').execute()
        logging.info(f"Successfully authenticated as: {user_profile.get('emailAddress')}")
        
        return service

    except Exception as e:
        logging.error(f"Authentication error: {str(e)}")
        raise

def get_account_email(service, user_id='me'):
    """Retrieve the email address of the authenticated Gmail account."""
    try:
        profile = service.users().getProfile(userId=user_id).execute()
        email_address = profile.get('emailAddress')
        logging.info(f"Authenticated Email Address: {email_address}")
        return email_address
    except Exception as e:
        logging.error(f"Error retrieving account email: {str(e)}")
        return None
# import os
# import pickle
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from googleapiclient.discovery import build
# from google_auth_oauthlib.flow import InstalledAppFlow
# import webbrowser



# # Set the scope for Gmail API
# SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# TOKEN_PATH = './_secrets/token.pickle'
# CREDENTIALS_PATH = './_secrets/credentials.json'

# def authenticate_gmail():
#     creds = None

#     # Check if the token file exists
#     if os.path.exists(TOKEN_PATH):
#         creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

#     # If no valid credentials, start the authentication flow
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 CREDENTIALS_PATH, SCOPES
#             )
#             creds = flow.run_local_server(
#                 port=8080, access_type='offline', prompt='consent'
#             )

#         # Save the credentials to the token file
#         with open(TOKEN_PATH, 'w') as token:
#             token.write(creds.to_json())

#     return build('gmail', 'v1', credentials=creds, cache_discovery=False)


# def authenticate_gmail():
#     """
#     Authenticate and return the Gmail API service with auto-refresh support.
#     Ensures tokens are refreshed or reauthenticated as needed.
#     """
#     creds = None
#     token_path = '_secrets/token.pickle'
#     credentials_path = '_secrets/credentials.json'

#     # Load existing credentials if token.pickle exists
#     if os.path.exists(token_path):
#         with open(token_path, 'rb') as token_file:
#             creds = pickle.load(token_file)

#     # Refresh expired credentials or reauthenticate if necessary
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             print("Refreshing access token...")
#             creds.refresh(Request())
#         else:
#             print("No valid credentials. Performing authentication.")
#             flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
#             flow.redirect_uri = "http://localhost:8080/"  # Set redirect URI explicitly
#             creds = flow.run_local_server(port=8080)
        
#         # Save updated credentials to token.pickle
#         with open(token_path, 'wb') as token_file:
#             pickle.dump(creds, token_file)

#     # Build and return the Gmail API service
#     return build('gmail', 'v1', credentials=creds)

# def authenticate_gmail():
#     """Authenticate and get the Gmail API service"""
#     creds = None

#     # Check if token.pickle already exists for storing user credentials
#     if os.path.exists('_secrets/token.pickle'):
#         with open('_secrets/token.pickle', 'rb') as token:
#             creds = pickle.load(token)

#     # If no valid credentials, ask user to log in
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 '_secrets/credentials.json', SCOPES
#             )
#             # Explicitly set redirect_uri for debugging
#             flow.redirect_uri = "http://localhost:8080/"
#             creds = flow.run_local_server(port=8080)
#         # Save credentials for next run
#         with open('_secrets/token.pickle', 'wb') as token:
#             pickle.dump(creds, token)

#     # Build the Gmail API service
#     return build('gmail', 'v1', credentials=creds)

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





