from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from groq import Groq
from datetime import datetime
import email.utils
import os

app = FastAPI()

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"]       = "86400"
        return response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


def groq_client():
    return Groq(api_key=os.environ["GROQ_API_KEY"])


class ChatRequest(BaseModel):
    query:         str
    emails:        list
    history:       list = []
    userName:      str  = "there"
    mode:          str  = "general"   # "general" | "search"
    gmailQuery:    str  = ""
    searchCount:   int  = 0

class DraftReplyRequest(BaseModel):
    emailFrom:    str
    emailSubject: str
    emailSnippet: str
    userName:     str = "there"

class SummarizeRequest(BaseModel):
    emails: list


# ── Helpers ───────────────────────────────────────────────────────────
def parse_date(raw: str) -> str:
    try:
        t = email.utils.parsedate_to_datetime(raw)
        return t.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return raw[:30] if raw else "Unknown"

def clean_sender(raw: str) -> str:
    if '<' in raw:
        name = raw.split('<')[0].strip().strip('"')
        return name or raw.split('<')[1].rstrip('>')
    return raw[:50]

def build_email_list(emails: list) -> str:
    lines = []
    for i, e in enumerate(emails[:80], 1):
        date   = parse_date(e.get('date', ''))
        sender = clean_sender(e.get('from', ''))
        subj   = e.get('subject', '(No subject)')[:100]
        snip   = e.get('snippet', '')[:200]
        lines.append(f"{i}. [{date}] From: {sender} | Subject: {subj}\n   Preview: {snip}")
    return "\n".join(lines)


# ── Endpoints ─────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    today = datetime.now().strftime("%B %d, %Y (%A)")
    email_list = build_email_list(req.emails)

    if req.mode == "search":
        # Search mode: AI only sees the search results
        if len(req.emails) == 0:
            # Gmail returned nothing
            system = f"""You are Aria, the AI email assistant for {req.userName}. Today is {today}.

A Gmail search was performed for: "{req.gmailQuery}"
Result: 0 emails found.

Tell the user clearly that no emails were found matching their query.
Suggest they check spelling, try a broader time range, or check a different Gmail tab."""
        else:
            system = f"""You are Aria, the AI email assistant for {req.userName}. Today is {today}.

A Gmail search for "{req.gmailQuery}" returned {len(req.emails)} email(s).
These are the EXACT matching emails from Gmail — answer ONLY based on these:

{email_list}

Rules:
- These ARE the real results. Do not say you "can't find" them.
- List them clearly with sender, subject, and date
- Be concise and direct"""
    else:
        # General mode: answer from pre-loaded emails
        system = f"""You are Aria, a world-class AI email chief of staff for {req.userName}.
Today is {today}. You have access to {req.userName}'s {len(req.emails)} most recent emails.

{email_list}

━━━ RULES ━━━
ACCURACY:
- Only state facts visible above. Never invent email content.
- For date queries: match against the [date] shown for each email precisely
- If something isn't in the list, say "I can see your {len(req.emails)} most recent emails and didn't find it — try asking me to search by sender name or date"

REPLY DETECTION (when asked which emails need a reply):
- NEEDS REPLY: real human asking a question, awaiting confirmation, personal message, job/interview
- NO REPLY: OTP, bank alerts, newsletters, order updates, noreply@, marketing, notifications
- Always show: sender + subject + one-line reason

FORMATTING:
- Numbered lists for multiple items
- **Bold** key info
- Be concise — {req.userName} is busy

IDENTITY: You are Aria. "I'm Aria, your personal AI email assistant built to make inbox zero actually possible." """

    messages = [{"role": "system", "content": system}]
    for h in req.history[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.query})

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.3,
        )
        return {"reply": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft-reply")
def draft_reply(req: DraftReplyRequest):
    prompt = f"""Write a natural email reply from {req.userName}.

Original email:
- From: {req.emailFrom}
- Subject: {req.emailSubject}
- Content: {req.emailSnippet}

Write like a real human. 3-5 sentences max. No filler phrases like "I hope this email finds you well."
Do NOT use placeholders. Sign off as {req.userName}.
Return ONLY the email body."""

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.5,
        )
        return {"draft": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    email_list = build_email_list(req.emails)
    prompt = f"""Summarise this inbox in 3 bullets. Focus on what actually matters.

{email_list}

Format:
• [Key point]
• [Key point]
• [Key point]

Max 12 words per bullet. Be specific, not generic."""

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return {"summary": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
