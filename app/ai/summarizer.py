import json
import anthropic
import streamlit as st


def _client():
    return anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])


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
    Single Claude call: returns (summaries, actions) — both are lists aligned to `emails`.
    Summaries: short one-sentence string with emoji.
    Actions: short action string or None.
    """
    email_block = _email_lines(emails)

    prompt = f"""You are an email assistant. Analyse each email and return a JSON object with two keys:
- "summaries": array of one-sentence summaries (max 12 words each, start with a relevant emoji)
- "actions": array of action items (max 10 words each) or null if no action is required

Emails:
{email_block}

Return ONLY valid JSON, no explanation. Example format:
{{"summaries": ["📦 Package arriving Tuesday.", "📅 Meeting at 10 AM tomorrow."], "actions": [null, "Confirm attendance by end of day."]}}"""

    try:
        resp = _client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.content[0].text)
        summaries = data.get("summaries", [None] * len(emails))
        actions   = data.get("actions",   [None] * len(emails))
        return summaries, actions
    except Exception:
        return [None] * len(emails), [None] * len(emails)


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
        resp = _client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=350,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"Could not generate briefing: {e}"
