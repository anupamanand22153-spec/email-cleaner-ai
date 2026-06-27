from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from groq import Groq
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
    query:    str
    emails:   list
    history:  list = []
    userName: str  = "there"

class DraftReplyRequest(BaseModel):
    emailFrom:    str
    emailSubject: str
    emailSnippet: str
    userName:     str = "there"

class SummarizeRequest(BaseModel):
    emails: list


def parse_date(raw: str) -> str:
    """Convert Gmail date header to clean readable format."""
    import email.utils, datetime
    try:
        t = email.utils.parsedate_to_datetime(raw)
        return t.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return raw[:30] if raw else "Unknown date"

def extract_sender(raw: str) -> str:
    """Get clean sender name from 'Name <email>' format."""
    if '<' in raw:
        return raw.split('<')[0].strip().strip('"') or raw.split('<')[1].rstrip('>')
    return raw[:40]

def build_context(emails):
    from datetime import datetime
    today = datetime.now().strftime("%B %d, %Y (%A)")
    lines = [
        f"TODAY'S DATE: {today}",
        f"LOADED EMAILS: {len(emails)} most recent emails shown below.",
        f"NOTE: User's full inbox may have many more emails. If asked about something not found here, say you can only see the {len(emails)} most recent and suggest they search.",
        "",
        "EMAILS (newest first):",
    ]
    for i, e in enumerate(emails[:80], 1):
        date   = parse_date(e.get('date', ''))
        sender = extract_sender(e.get('from', ''))
        subj   = e.get('subject', '(No subject)')[:80]
        snip   = e.get('snippet', '')[:150]
        lines.append(f"{i}. [{date}] From: {sender} | Subject: {subj} | Preview: {snip}")
    return "\n".join(lines)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    context = build_context(req.emails)
    system = f"""You are Aria, a world-class AI email chief of staff for {req.userName}. You are precise, honest, and highly intelligent.

{context}

━━━ YOUR RULES ━━━

ACCURACY FIRST:
- Only state facts visible in the email data above
- If an email is NOT in the data, say "I can only see your {len(req.emails)} most recent emails and didn't find it — try asking me to search specifically"
- Never make up email content, dates, or senders
- When asked about a date like "27th", match it against the [Date] field of each email — be exact

REPLY DETECTION:
- NEEDS REPLY → real human asked a direct question, awaiting your response, sent a personal message, interview/job offer
- NO REPLY NEEDED → OTP codes, bank alerts, newsletters, order updates, noreply@, marketing, notifications, social media alerts
- When listing emails needing reply: show From + Subject + one-line reason

FORMATTING:
- Use numbered lists for multiple emails
- Bold key info with **text**
- Keep responses tight — {req.userName} is busy
- If nothing matches, say so confidently rather than guessing

IDENTITY:
- You are Aria. If asked who you are: "I'm Aria, your personal AI email assistant built to make inbox zero actually possible."
"""

    messages = [{"role": "system", "content": system}]
    for h in req.history[-8:]:
        messages.append({"role": h.get("role","user"), "content": h.get("content","")})
    messages.append({"role": "user", "content": req.query})

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.5,
        )
        return {"reply": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft-reply")
def draft_reply(req: DraftReplyRequest):
    prompt = f"""You are writing an email reply on behalf of {req.userName}. Write like a real human, not a corporate robot.

Original email:
- From: {req.emailFrom}
- Subject: {req.emailSubject}
- Content: {req.emailSnippet}

Rules:
- Sound natural and warm, like how {req.userName} would actually write
- Be concise — 3-5 sentences maximum
- Address the specific question or request in the email
- Do NOT use filler phrases like "I hope this email finds you well" or "Please don't hesitate"
- Do NOT add placeholders like [Your Name] — sign off as {req.userName}
- Return ONLY the email body text, nothing else"""

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.6,
        )
        return {"draft": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    context = build_context(req.emails)
    prompt = f"""Give a brief 3-bullet summary of this inbox. Focus on what's important.

{context}

Format:
• [Key point 1]
• [Key point 2]
• [Key point 3]

Be concise — max 10 words per bullet."""

    try:
        resp = groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.4,
        )
        return {"summary": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
