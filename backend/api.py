from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI(title="Email Cleaner AI Backend")

# ── Force CORS on every response including preflight ──────────────────
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


def client():
    return Groq(api_key=os.environ["GROQ_API_KEY"])


# ── Models ────────────────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────
def build_email_context(emails: list) -> str:
    lines = [f"INBOX ({len(emails)} emails):"]
    for i, e in enumerate(emails[:40], 1):
        lines.append(f"{i}. From: {e.get('from','')[:50]} | Subject: {e.get('subject','')[:80]} | Preview: {e.get('snippet','')[:100]}")
    return "\n".join(lines)


# ── Endpoints ─────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(req: ChatRequest):
    context = build_email_context(req.emails)
    system  = f"""You are a smart AI email assistant for {req.userName}.
You have access to their inbox shown below.

{context}

Guidelines:
- Answer concisely and helpfully in 1-3 short paragraphs
- Reference specific emails when relevant
- Give actionable recommendations
- Be warm and personal"""

    messages = [{"role": "system", "content": system}]
    for h in req.history[-8:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.query})

    try:
        resp = client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=500,
            temperature=0.5,
        )
        return {"reply": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft-reply")
def draft_reply(req: DraftReplyRequest):
    prompt = f"""Write a professional, friendly email reply on behalf of {req.userName}.

Original email:
- From: {req.emailFrom}
- Subject: {req.emailSubject}
- Content preview: {req.emailSnippet}

Rules:
- Start with an appropriate greeting
- Keep it concise (3-5 sentences max)
- Sound natural, not robotic
- End with a polite sign-off using {req.userName}'s name
- Do not add placeholders like [Your Name] — use the actual name
- Return ONLY the email body, no subject line"""

    try:
        resp = client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.6,
        )
        return {"draft": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
def summarize(req: SummarizeRequest):
    context = build_email_context(req.emails)
    prompt  = f"""Give a brief 3-bullet summary of this inbox. Focus on what's important.

{context}

Format:
• [Key point 1]
• [Key point 2]
• [Key point 3]

Be concise — max 10 words per bullet."""

    try:
        resp = client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.4,
        )
        return {"summary": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# trigger redeploy
