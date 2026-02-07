from googleapiclient.discovery import build


def get_gmail_service(credentials):
    """
    Create and return Gmail API service
    """
    service = build("gmail", "v1", credentials=credentials)
    return service


def fetch_email_metadata(service, max_results=10):
    """
    Fetch email headers only (From, Subject, Date)
    READ-ONLY SAFE MODE
    """
    results = service.users().messages().list(
        userId="me",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    email_data = []

    for msg in messages:
        msg_detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = msg_detail["payload"]["headers"]

        email = {
            "From": "",
            "Subject": "",
            "Date": ""
        }

        for h in headers:
            if h["name"] in email:
                email[h["name"]] = h["value"]

        email_data.append(email)

    return email_data
