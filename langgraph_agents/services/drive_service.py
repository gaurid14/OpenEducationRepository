import json

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_drive_service():
    """Authenticate with personal Google Drive using OAuth token."""
    with open(settings.GOOGLE_TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    service = build("drive", "v3", credentials=creds)
    return service


def get_or_create_drive_folder(service, folder_name, parent_id=None):
    """Get folder ID if exists, else create and return ID."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    result = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = result.get('files', [])
    if files:
        return files[0]['id']

    # Create folder only if it doesn't exist
    metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        metadata['parents'] = [parent_id]

    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']
