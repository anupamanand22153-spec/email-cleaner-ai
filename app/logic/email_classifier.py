import re

# ── SPAM ────────────────────────────────────────────────────────────
SPAM_SUBJECT_KEYWORDS = [
    # Classic scams
    "you have won", "you've won", "you are selected", "you've been selected",
    "congratulations", "winner", "lottery", "prize", "claim your",
    "claim now", "you are a winner", "lucky draw", "lucky winner",
    "inheritance", "nigerian", "wire transfer", "million dollars",
    "free money", "make money fast", "earn money online",
    "work from home earn", "get rich", "investment opportunity",
    "double your money", "guaranteed income", "passive income guaranteed",
    # Phishing
    "verify your account", "confirm your account", "account suspended",
    "account will be closed", "account has been compromised",
    "unusual activity detected", "suspicious login", "security breach",
    "update your billing", "update payment information", "payment failed",
    "your card has been", "bank account suspended", "click to verify",
    "click here to confirm", "validate your email", "re-verify",
    # Health/weight scams
    "lose weight fast", "lose 30 pounds", "burn fat fast",
    "miracle cure", "doctors hate", "one weird trick",
    "anti-aging secret", "boost testosterone", "enlarge",
    # Crypto/financial scams
    "bitcoin investment", "crypto opportunity", "guaranteed returns",
    "risk-free investment", "forex signal", "trading bot profit",
    # Generic spam signals
    "act now", "limited time offer", "expires today", "respond immediately",
    "do not ignore", "final notice", "last chance", "urgent response required",
    "free gift", "free iphone", "free laptop", "gift card",
    "porn", "adult", "dating site", "meet singles",
    "cheap meds", "pharmacy online", "viagra", "cialis",
]

SPAM_SENDER_PATTERNS = [
    r"[a-z0-9]{8,}@[a-z0-9]{5,}\.(xyz|top|click|loan|bid|win|download|review|country|stream|gdn|racing|faith|date|trade|webcam|science|accountant|men|work|party)$",
    r"no.?reply@.*(spam|bulk|mass|promo\d)",
    r"\d{6,}@",
    r"[a-z]{2}\d{4,}[a-z]{2}@",
]

SPAM_BODY_KEYWORDS = [
    "unsubscribe to stop receiving", "if you did not request this ignore",
    "this is not spam", "this email complies with", "can-spam",
    "to be removed from", "to opt out click",
    "sent to you because you", "you are receiving this because you signed up",
]

# ── PROMOTIONS ───────────────────────────────────────────────────────
PROMOTIONAL_SUBJECT_KEYWORDS = [
    # Sales & discounts
    "% off", "save up to", "flat off", "up to off", "discount",
    "sale ends", "sale today", "mega sale", "big sale", "flash sale",
    "black friday", "cyber monday", "holiday sale", "clearance",
    "buy one get one", "bogo", "2 for 1",
    # Offers
    "exclusive offer", "special offer", "limited offer", "best deal",
    "today only", "weekend deal", "daily deal", "hot deal",
    "coupon", "voucher", "promo code", "use code", "redeem",
    "cashback", "rebate", "refund offer", "reward",
    # Marketing language
    "don't miss", "don't miss out", "hurry", "while supplies last",
    "new arrival", "new collection", "just launched", "now available",
    "shop now", "buy now", "order now", "get yours",
    "free shipping", "free delivery", "free trial",
    "introducing", "announcing", "we're excited to",
    # Newsletters
    "newsletter", "weekly digest", "monthly update", "roundup",
    "our latest", "this week in", "what's new", "highlights from",
    "top stories", "trending now",
    # Subscriptions/marketing
    "subscription", "upgrade your plan", "premium plan",
    "you're invited", "webinar", "join us", "register now",
]

PROMOTIONAL_SENDER_PATTERNS = [
    "no-reply", "noreply", "donotreply", "do-not-reply",
    "newsletter", "updates", "notifications", "mailer",
    "marketing", "promotions", "offers", "deals", "sales",
    "info@", "hello@", "hi@", "team@", "support@",
    "news@", "digest@", "alert@", "notify@",
]

KNOWN_PROMO_SENDERS = [
    "amazon", "flipkart", "ebay", "walmart", "target", "bestbuy",
    "linkedin", "twitter", "facebook", "instagram", "youtube",
    "netflix", "spotify", "uber", "lyft", "airbnb",
    "swiggy", "zomato", "myntra", "meesho", "ajio",
    "booking.com", "expedia", "tripadvisor", "makemytrip",
    "medium", "substack", "mailchimp", "hubspot",
    "coursera", "udemy", "skillshare", "edx",
    "nykaa", "bigbasket", "grofers", "blinkit",
    "dominos", "mcdonalds", "kfc", "starbucks",
    "paypal", "razorpay", "stripe", "paytm",
]

# ── IMPORTANT ────────────────────────────────────────────────────────
IMPORTANT_KEYWORDS = [
    # Finance & banking
    "invoice", "receipt", "payment received", "payment due",
    "transaction", "bank statement", "account statement",
    "tax return", "tax filing", "irs", "income tax",
    "salary", "payslip", "payroll", "reimbursement",
    "loan approved", "loan application", "emi",
    # Security
    "otp", "one-time password", "two-factor", "2fa",
    "security code", "verification code", "login attempt",
    "password reset", "password changed", "new device",
    # Work & career
    "job offer", "offer letter", "interview", "interview scheduled",
    "application received", "shortlisted", "hired",
    "meeting", "meeting invitation", "calendar invite",
    "project deadline", "action required", "urgent",
    "please review", "response needed", "awaiting your",
    # Legal & government
    "legal notice", "court", "lawsuit", "compliance",
    "government", "passport", "visa", "immigration",
    "driving license", "id proof", "aadhaar", "pan card",
    # Health
    "appointment", "appointment confirmed", "test results",
    "medical report", "prescription", "hospital",
    "doctor", "clinic", "health insurance",
    # Travel & bookings
    "booking confirmed", "reservation", "flight", "hotel",
    "ticket", "boarding pass", "itinerary", "check-in",
    # Education
    "admission", "acceptance", "result", "examination",
    "scholarship", "enrollment", "registration confirmed",
    # Delivery & orders
    "order confirmed", "order shipped", "out for delivery",
    "delivered", "tracking", "shipment",
]

IMPORTANT_SENDERS = [
    "bank", "govt", "gov", "irs", "income-tax", "nsdl",
    "hospital", "clinic", "university", "college", "school",
    "court", "legal", "insurance",
]


def _is_suspicious_sender(sender: str) -> bool:
    """Detect randomly generated spam sender addresses."""
    for pattern in SPAM_SENDER_PATTERNS:
        if re.search(pattern, sender):
            return True
    local = sender.split("@")[0] if "@" in sender else sender
    if len(local) > 12 and sum(c.isdigit() for c in local) > 4:
        return True
    return False


def classify_email(email: dict) -> str:
    subject = (email.get("Subject") or "").lower()
    sender  = (email.get("From")    or "").lower()
    snippet = (email.get("snippet") or "").lower()
    text    = f"{subject} {snippet}"

    # ── SPAM detection (strict) ──────────────────────────────────
    for kw in SPAM_SUBJECT_KEYWORDS:
        if kw in subject:
            return "Spam"

    if _is_suspicious_sender(sender):
        return "Spam"

    for kw in SPAM_BODY_KEYWORDS:
        if kw in snippet:
            return "Spam"

    # ── IMPORTANT detection ──────────────────────────────────────
    for kw in IMPORTANT_KEYWORDS:
        if kw in text:
            return "Important"

    for kw in IMPORTANT_SENDERS:
        if kw in sender:
            return "Important"

    # ── PROMOTIONS detection ─────────────────────────────────────
    for kw in PROMOTIONAL_SUBJECT_KEYWORDS:
        if kw in subject:
            return "Promotions"

    for pattern in PROMOTIONAL_SENDER_PATTERNS:
        if pattern in sender:
            return "Promotions"

    for brand in KNOWN_PROMO_SENDERS:
        if brand in sender:
            return "Promotions"

    return "Other"


def classify_emails(emails: list) -> list:
    for email in emails:
        email["Category"] = classify_email(email)
    return emails
