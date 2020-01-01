import pickle
import os.path
import sys

import requests
import sqlite_utils
from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# The labels from where to get the messages (only starred by default)
# Other possible values can include:
# IMPORTANT, INBOX, UNREAD, CATEGORY_UPDATES, CATEGORY_PROMOTIONS, CATEGORY_PERSONAL, CATEGORY_SOCIAL
# Note that the script doesn't check for duplicates when running the first time and mails are in more than one category.
LABEL_IDS = ['STARRED']
USER_ID = 'me'
EMAIL_URL = 'https://mail.google.com/mail/#all/'
DYNALIST_INBOX_URL = 'https://dynalist.io/api/v1/inbox/add'
DYNALIST_TOKEN_FILENAME = 'dynalistToken.txt'
EMAILS_DB_FILENAME = 'emails.db'
EMAILS_DB_TABLE = 'emails'


def build_gmail_api_service():
    """
    Downloads all the starred messages from gmail
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as gmail_auth_token:
            creds = pickle.load(gmail_auth_token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as gmail_auth_token:
            pickle.dump(creds, gmail_auth_token)

    return build('gmail', 'v1', credentials=creds)


def download_messages(gmail_service):
    # Get the messages
    try:
        response = gmail_service.users().messages().list(userId=USER_ID, labelIds=LABEL_IDS).execute()

        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = gmail_service.users().messages().list(userId=USER_ID,
                                                             labelIds=LABEL_IDS,
                                                             pageToken=page_token).execute()
            messages.extend(response['messages'])

        return messages

    except errors.HttpError as error:
        print('An error occurred downloading the messages: %s' % error)


def process_message(gmail_service, emails_db, message_id, dynalist_token):
    try:
        message = gmail_service.users().messages().get(userId=USER_ID,
                                                       id=message_id,
                                                       format='metadata',
                                                       metadataHeaders=['Subject']).execute()

        subject = message['payload']['headers'][0]['value']
        message_url = construct_message_url(message_id)

        if check_email_against_db(emails_db, message_id):
            print('Message with id ' + message_id + ' and subject ' + subject + ' will be posted to Dynalist')
            # post_to_dynalist(dynalist_token, subject, message_url)
            save_email_to_db(emails_db, message_id)
        else:
            print('Message with id ' + message_id + ' and subject ' + subject + ' already added to Dynalist. Skipping.')

    except errors.HttpError as error:
        print('An error occured downloading the message: %s' % error)


def construct_message_url(message_id):
    return EMAIL_URL + message_id


def get_dynalist_token():
    if not os.path.exists(DYNALIST_TOKEN_FILENAME):
        sys.exit('The dynalist token file ' + DYNALIST_TOKEN_FILENAME + ' does not exist')

    with open(DYNALIST_TOKEN_FILENAME, 'rb') as token_file:
        return token_file.readline()


def post_to_dynalist(dynalist_token, subject, message_url):
    """
    POSTs the message with subject and message_url to Dynalist
    """
    request_body = {
        "token": dynalist_token,
        "content": subject,
        "note": message_url
    }

    r = requests.post(DYNALIST_INBOX_URL, json=request_body)
    if r.status_code != 200:
        sys.exit('Failed to POST to Dynalist. Status code is: ' + r.status_code + ". Reason is: " + r.reason)

    response = r.json()
    response_code = response['_code']
    if response_code != 'Ok':
        msg = response['_msg']
        sys.exit("Cannot create Dynalist node. Response code is " + response_code + " and the error message is " + msg)


def check_email_against_db(emails_db, message_id):
    """
    Checks if the message with message_id exists in the database or not.
    Returns True if the message is not already saved in the database.
    """
    try:
        emails_db[EMAILS_DB_TABLE].get(message_id)
    except sqlite_utils.db.NotFoundError:
        return True
    return False

def save_email_to_db(emails_db, message_id):
    """
    Saves the message_id in the database
    """
    emails_db[EMAILS_DB_TABLE].insert({"id" : message_id}, pk="id")


if __name__ == '__main__':
    service = build_gmail_api_service()
    downloaded_messages = download_messages(service)

    token = get_dynalist_token()
    db = sqlite_utils.Database(EMAILS_DB_FILENAME)
    table = db[EMAILS_DB_TABLE]

    if not table.exists:
        table.create({"id": str}, pk="id")

    for downloaded_message in downloaded_messages:
        process_message(service, db, downloaded_message['id'], token.decode('utf-8'))
