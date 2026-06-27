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


def build_context(emails):
    lines = [f"INBOX ({len(emails)} emails):"]
    for i, e in enumerate(emails[:80], 1):
        lines.append(
            f"{i}. Date: {e.get('date','')[:30]} | From: {e.get('from','')[:50]} | Subject: {e.get('subject','')[:80]} | Preview: {e.get('snippet','')[:120]}"
        )
    return "\n".join(lines)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    context = build_context(req.emails)
    system = f"""You are Aria, an elite AI email chief of staff for {req.userName}. You have deep expertise in email triage and human communication patterns.
Your name is Aria. If someone asks who you are, say: "I'm Aria, your personal AI email assistant."

INBOX DATA:
{context}

CORE INTELLIGENCE RULES:

1. NEVER-REPLY emails (automated systems, not humans):
   - Sender contains: noreply, no-reply, donotreply, notifications, alerts, mailer, newsletter, updates, support@, info@, hello@company
   - OTP / verification codes, bank transaction alerts, order confirmations, shipping updates
   - Marketing emails, promotional offers, discount codes, newsletters
   - Social media notifications (LinkedIn, Twitter, Instagram)
   - Automated receipts, invoices from services

2. NEEDS-REPLY emails (real human expects a response):
   - A real person directly asked you a question
   - Someone invited you to something and is waiting for your confirmation
   - A colleague, client, or friend sent a personal message
   - A job recruiter or interviewer reached out
   - Someone explicitly said "please respond", "let me know", "waiting for your reply"

3. SMART REASONING:
   - Read the snippet carefully — does a human need your response, or is this just FYI?
   - Prioritize by urgency + relationship (boss > colleague > stranger > company)
   - Be concise and direct — {req.userName} is busy

4. FORMAT:
   - When listing emails, always include: From, Subject, why it needs action
   - Never recommend replying to automated emails
   - If nothing truly needs a reply, say so confidently"""

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
