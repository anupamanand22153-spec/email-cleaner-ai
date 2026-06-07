"""
Rule-based Email Classifier
"""

SPAM_KEYWORDS = [
    "spam", "phishing", "scam", "lottery", "winner", "prize", "claim now",
    "you have won", "free money", "nigerian", "inheritance", "wire transfer",
    "click here to claim", "verify your account immediately", "urgent action",
    "your account will be suspended", "confirm your identity",
]

SPAM_DOMAINS = [
    "spam", "phish", "temp-mail", "guerrillamail", "mailinator",
]

PROMOTIONAL_KEYWORDS = [
    "sale", "sales", "offer", "offers", "discount", "deal", "deals",
    "promo", "promotion", "promotions", "coupon", "voucher", "savings",
    "save", "% off", "limited time", "buy now", "shop now", "order now",
    "free shipping", "subscribe", "unsubscribe", "newsletter", "marketing",
    "advertis", "sponsored", "no-reply", "noreply", "donotreply",
    "do-not-reply", "bulk", "campaign", "offer letter" , "black friday",
    "cyber monday", "flash sale", "clearance", "exclusive deal",
    "reward", "rewards", "cashback", "refund", "rebate",
]

PROMOTIONAL_SENDERS = [
    "offers", "deals", "sales", "promotions", "newsletter", "marketing",
    "noreply", "no-reply", "donotreply", "do-not-reply", "notifications",
    "updates", "info@", "hello@", "hi@", "team@",
]

IMPORTANT_KEYWORDS = [
    "invoice", "receipt", "payment", "paid", "transaction", "bank",
    "alert", "security", "password", "reset", "verify", "verification",
    "otp", "one-time", "two-factor", "2fa", "login", "sign-in",
    "meeting", "interview", "job", "appointment", "schedule",
    "deadline", "urgent", "action required", "important", "account",
    "statement", "tax", "insurance", "hospital", "medical", "doctor",
    "visa", "passport", "ticket", "booking", "confirmation", "order",
    "shipment", "delivery", "shipped", "package", "tracking",
    "contract", "agreement", "legal", "court", "government",
    "university", "college", "admission", "result", "exam",
]


def classify_email(email: dict) -> str:
    """
    Classify a single email as: Important | Promotions | Spam | Other
    """
    subject = (email.get("Subject") or "").lower()
    sender = (email.get("From") or "").lower()
    text = f"{subject} {sender}"

    # Check spam first
    for word in SPAM_KEYWORDS:
        if word in text:
            return "Spam"
    for domain in SPAM_DOMAINS:
        if domain in sender:
            return "Spam"

    # Check important
    for word in IMPORTANT_KEYWORDS:
        if word in text:
            return "Important"

    # Check promotional
    for word in PROMOTIONAL_KEYWORDS:
        if word in text:
            return "Promotions"
    for word in PROMOTIONAL_SENDERS:
        if word in sender:
            return "Promotions"

    return "Other"


def classify_emails(emails: list) -> list:
    for email in emails:
        email["Category"] = classify_email(email)
    return emails
