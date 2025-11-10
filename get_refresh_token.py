from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/drive.file']

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret_761045060415-dn8kaq0qj0ff9pk92o7rj6kld5eg5b38.apps.googleusercontent.com.json', SCOPES)  # your downloaded OAuth JSON
creds = flow.run_local_server(port=8000)

# Print tokens
print("Access Token:", creds.token)
print("Refresh Token:", creds.refresh_token)

# Save to a JSON file
with open("token.json", "w") as f:
    json.dump({
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }, f)
