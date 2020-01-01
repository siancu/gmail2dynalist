import pickle
import os.path

from googleapiclient import errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# The labels from where to get the messages (only starred by default)
# Other possible values can include IMPORTANT, INBOX, UNREAD, CATEGORY_UPDATES, CATEGORY_PROMOTIONS, CATEGORY_PERSONAL, CATEGORY_SOCIAL
# Note that the script doesn't check for duplicates when running the first time and mails are in more than one category.
LABEL_IDS = ['STARRED']
USER_ID = 'me'
EMAIL_URL = 'https://mail.google.com/mail/#all/'


def download_mails():
    """
    Downloads all the starred messages from gmail
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # Get the messages
    try:
        response = service.users().messages().list(userId=USER_ID, labelIds=LABEL_IDS).execute()

        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=USER_ID,
                                                       labelIds=LABEL_IDS,
                                                       pageToken=page_token).execute()
            messages.extend(response['messages'])

        for message in messages:
            print(message['id'])

    except errors.HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    download_mails()
