from collections import Counter
from groq import Groq
import streamlit as st


def _client():
    return Groq(api_key=st.secrets["groq"]["api_key"])


def generate_weekly_report(user_name, classified):
    """Generate a weekly inbox report as HTML-friendly markdown string."""
    counts = Counter(cat for _, cat in classified)

    size_by_cat = {"Important": 0, "Promotions": 0, "Spam": 0, "Other": 0}
    for email, cat in classified:
        size_by_cat[cat] += email.get("sizeEstimate", 0)

    def fmt_size(b):
        if b >= 1_000_000: return f"{b/1_000_000:.1f} MB"
        if b >= 1_000:     return f"{b/1_000:.1f} KB"
        return f"{b} B"

    # Top senders from promotions
    import re
    def sender_name(h):
        m = re.match(r'^"?([^"<]+)"?\s*<', h)
        if m: return m.group(1).strip()
        m2 = re.search(r'[\w.+\-]+@[\w\-]+\.[a-zA-Z]+', h)
        if m2: return m2.group(0)
        return h.strip()

    promo_emails = [e for e, cat in classified if cat == "Promotions"]
    top_senders = Counter(sender_name(e.get("From", "")) for e in promo_emails).most_common(3)
    top_str = ", ".join(f"{s} ({c})" for s, c in top_senders) or "None"

    important_subjects = [
        e.get("Subject", "")[:80] for e, cat in classified if cat == "Important"
    ][:5]
    important_str = "\n".join(f"- {s}" for s in important_subjects) or "- None"

    prompt = f"""Write a friendly weekly inbox report for {user_name}.

This week's stats (last 100 emails analysed):
- Important: {counts.get('Important', 0)} emails ({fmt_size(size_by_cat['Important'])})
- Promotions: {counts.get('Promotions', 0)} emails ({fmt_size(size_by_cat['Promotions'])})
- Spam: {counts.get('Spam', 0)} emails ({fmt_size(size_by_cat['Spam'])})
- Other: {counts.get('Other', 0)} emails ({fmt_size(size_by_cat['Other'])})
- Total storage: {fmt_size(sum(size_by_cat.values()))}

Top promotional senders: {top_str}

Important emails:
{important_str}

Write a 6-8 line report. Include:
1. A greeting: "Hi {user_name},"
2. Quick summary of inbox health
3. 2-3 specific actionable insights
4. One encouraging closing line
Keep it warm, concise, and useful."""

    try:
        resp = _client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate report: {e}"
