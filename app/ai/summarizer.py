import json
import streamlit as st
from groq import Groq


def _client():
    return Groq(api_key=st.secrets["groq"]["api_key"])


def _email_lines(emails):
    lines = []
    for i, e in enumerate(emails, 1):
        sender  = e.get("From", "")[:60]
        subject = e.get("Subject", "")[:120]
        snippet = e.get("snippet", "")[:200]
        lines.append(f"{i}. From: {sender} | Subject: {subject} | Preview: {snippet}")
    return "\n".join(lines)


def summarize_and_extract(emails):
    """
    Single Groq call: returns (summaries, actions) aligned to `emails`.
    Summaries: one-sentence string with emoji.
    Actions: short action string or None.
    """
    email_block = _email_lines(emails)

    prompt = f"""You are an email assistant. Analyse each email and return a JSON object with two keys:
- "summaries": array of one-sentence summaries (max 12 words each, start with a relevant emoji)
- "actions": array of action items (max 10 words each) or null if no action is required

Emails:
{email_block}

Return ONLY valid JSON, no explanation. Example:
{{"summaries": ["📦 Package arriving Tuesday.", "📅 Meeting at 10 AM tomorrow."], "actions": [null, "Confirm attendance by end of day."]}}"""

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        summaries = data.get("summaries", [None] * len(emails))
        actions   = data.get("actions",   [None] * len(emails))
        return summaries, actions
    except Exception:
        return [None] * len(emails), [None] * len(emails)


def build_email_context(classified):
    """Build a compact inbox context string for the chat system prompt."""
    from collections import Counter
    counts = Counter(cat for _, cat in classified)

    lines = [
        "INBOX SUMMARY:",
        f"- Important: {counts.get('Important', 0)} emails",
        f"- Promotions: {counts.get('Promotions', 0)} emails",
        f"- Spam: {counts.get('Spam', 0)} emails",
        f"- Other: {counts.get('Other', 0)} emails",
        f"\nEMAILS (up to 60, most recent first):",
    ]

    for i, (email, cat) in enumerate(classified[:60], 1):
        sender  = email.get("From", "")[:50]
        subject = email.get("Subject", "")[:80]
        snippet = email.get("snippet", "")[:100]
        lines.append(f"{i}. [{cat}] From: {sender} | Subject: {subject} | Preview: {snippet}")

    return "\n".join(lines)


def chat_with_inbox(user_message, email_context, history, user_name):
    """
    Multi-turn chat about the inbox.
    history: list of {role, content} dicts (excludes current message).
    Returns assistant reply string.
    """
    system_prompt = f"""You are a smart, friendly AI email assistant for {user_name}.
You have full access to their Gmail inbox data shown below.

{email_context}

Guidelines:
- Answer concisely and helpfully
- When listing emails, show sender + subject + category
- Give specific, actionable recommendations when asked
- If asked "what should I do today?", prioritise Important emails with action items
- Keep replies under 200 words unless the user asks for detail
- Be warm and personal — you know their inbox well"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-12:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=600,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, something went wrong: {e}"


def classify_emails_batch(emails):
    """
    AI-powered batch classification of emails.
    Returns a list of categories aligned to `emails`.
    Categories: Important | Promotions | Spam | Other
    """
    lines = []
    for i, e in enumerate(emails, 1):
        sender  = e.get("From", "")[:80]
        subject = e.get("Subject", "")[:120]
        snippet = e.get("snippet", "")[:150]
        gmail_spam = " [GMAIL_MARKED_SPAM]" if e.get("_gmail_spam") else ""
        lines.append(f"{i}. From: {sender} | Subject: {subject} | Preview: {snippet}{gmail_spam}")
    email_block = "\n".join(lines)

    prompt = f"""You are an expert email classifier. Classify each email into exactly one category:

- Important: personal emails, work/professional, banking/finance, OTP/security codes, invoices, meeting requests, job offers, medical, legal, order confirmations, flight/hotel bookings
- Promotions: marketing emails, newsletters, brand offers, discounts, sales, product launches, subscription updates from known companies
- Spam: scams, phishing, fake prizes/lotteries, suspicious senders, unsolicited bulk emails, fake job offers, crypto scams, adult content, miracle cures. Emails tagged [GMAIL_MARKED_SPAM] should almost always be classified as Spam.
- Other: social media notifications, automated system alerts, GitHub/app notifications, receipts not fitting above

Emails to classify:
{email_block}

Return ONLY a JSON array of exactly {len(emails)} strings. Each string must be one of: "Important", "Promotions", "Spam", "Other".
Example for 3 emails: ["Important", "Spam", "Promotions"]
No explanation, no extra text — just the JSON array."""

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        categories = json.loads(text.strip())
        valid = {"Important", "Promotions", "Spam", "Other"}
        return [c if c in valid else "Other" for c in categories]
    except Exception:
        return None  # Caller falls back to rule-based


def search_emails(query, emails):
    """
    Natural language search across emails.
    Returns (answer: str, matching_indices: list[int])
    """
    email_block = _email_lines(emails)

    prompt = f"""You are an email search assistant. The user asked: "{query}"

Here are their emails (numbered from 1):
{email_block}

Respond with ONLY a JSON object:
{{
  "answer": "A direct 1-2 sentence response to the user's question",
  "indices": [0, 2, 5]
}}

Rules:
- indices must be 0-based (subtract 1 from the email number)
- If asking about specific senders or topics, list matching email indices
- If asking an analytical question ("needs reply", "urgent"), answer it and list relevant emails
- If nothing matches, return empty indices array and say so in the answer
- Return ONLY valid JSON, no extra text"""

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        return data.get("answer", ""), data.get("indices", [])
    except Exception as e:
        return f"Search failed: {e}", []


def generate_daily_briefing(user_name, classified):
    """Returns a personalized morning briefing string."""
    from collections import Counter
    counts = Counter(cat for _, cat in classified)

    important_emails = [e for e, cat in classified if cat == "Important"][:8]
    important_str = "\n".join(
        f"- {e.get('From','')[:40]} — {e.get('Subject','')[:80]}"
        for e in important_emails
    ) or "None"

    prompt = f"""Write a short, friendly morning inbox briefing for {user_name}.

Stats from their last {len(classified)} emails:
- Important: {counts.get('Important', 0)}
- Promotions: {counts.get('Promotions', 0)}
- Spam: {counts.get('Spam', 0)}
- Other: {counts.get('Other', 0)}

Important emails:
{important_str}

Rules:
- Start with "Good day, {user_name}."
- 3-5 bullet points max
- Each bullet is one actionable or informational line
- Be concise, warm, and useful
- Do NOT use headers or sub-sections"""

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate briefing: {e}"
