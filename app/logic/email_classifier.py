# app/logic/email_classifier.py

"""
Rule-based Email Classifier
Safe, fast, read-only, deployable
"""

PROMOTIONAL_KEYWORDS = [
    "sale", "offer", "discount", "deal", "promo",
    "limited time", "buy now", "subscribe", "unsubscribe",
    "newsletter", "marketing"
]

IMPORTANT_KEYWORDS = [
    "invoice", "receipt", "payment", "bank",
    "alert", "security", "password",
    "meeting", "interview", "job", "offer letter"
]


def classify_email(email: dict) -> str:
    """
    Classify a single email based on headers only
    Input: {From, Subject, Date}
    Output: Promotional | Important | Other
    """

    subject = (email.get("Subject") or "").lower()
    sender = (email.get("From") or "").lower()

    text = f"{subject} {sender}"

    for word in IMPORTANT_KEYWORDS:
        if word in text:
            return "Important"

    for word in PROMOTIONAL_KEYWORDS:
        if word in text:
            return "Promotional"

    return "Other"


def classify_emails(emails: list) -> list:
    """
    Classify list of emails
    Adds: email['Category']
    """

    classified = []

    for email in emails:
        email["Category"] = classify_email(email)
        classified.append(email)

    return classified
