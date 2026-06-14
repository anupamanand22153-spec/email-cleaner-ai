from googleapiclient.discovery import build


def get_gmail_service(credentials):
    return build("gmail", "v1", credentials=credentials)


def _fetch_from_label(service, label, max_results):
    """Fetch email metadata from a specific Gmail label."""
    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        labelIds=[label],
    ).execute()

    messages = results.get("messages", [])
    email_data = []

    for msg in messages:
        msg_detail = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()

        headers = msg_detail["payload"]["headers"]
        email = {"From": "", "Subject": "", "Date": "", "_label": label}

        for h in headers:
            if h["name"] in email:
                email[h["name"]] = h["value"]

        email["sizeEstimate"] = msg_detail.get("sizeEstimate", 0)
        email["snippet"]      = msg_detail.get("snippet", "")
        email_data.append(email)

    return email_data


def fetch_email_metadata(service, max_results=100):
    """
    Fetch emails from INBOX (85) + SPAM folder (15).
    Emails from SPAM label are pre-tagged so the classifier
    can confirm or override the category.
    """
    inbox_count = max(max_results - 15, 70)
    spam_count  = 15

    inbox_emails = _fetch_from_label(service, "INBOX", inbox_count)
    spam_emails  = _fetch_from_label(service, "SPAM",  spam_count)

    # Pre-tag Gmail spam so AI can use it as a signal
    for e in spam_emails:
        e["_gmail_spam"] = True

    return inbox_emails + spam_emails
