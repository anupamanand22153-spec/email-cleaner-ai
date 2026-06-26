// ── Config ────────────────────────────────────────────────────────────
const CLIENT_ID   = 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com'; // Replace after Google Cloud setup
const BACKEND_URL = 'https://your-backend.railway.app';                 // Replace after backend deployment
const SCOPES      = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
].join(' ');

// ── Message handler ───────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message).then(sendResponse).catch(err => sendResponse({ success: false, error: err.message }));
  return true;
});

async function handleMessage(message) {
  switch (message.type) {

    case 'AUTH': {
      const token    = await authenticate();
      const userInfo = await getUserInfo(token);
      await chrome.storage.local.set({ token, userInfo, authedAt: Date.now() });
      return { success: true, userInfo };
    }

    case 'GET_AUTH_STATUS': {
      const { token, userInfo } = await chrome.storage.local.get(['token', 'userInfo']);
      if (token) return { authenticated: true, userInfo };
      return { authenticated: false };
    }

    case 'FETCH_EMAILS': {
      const { token } = await chrome.storage.local.get('token');
      if (!token) throw new Error('Not authenticated');
      const emails = await fetchEmails(token, message.maxResults || 50);
      return { success: true, emails };
    }

    case 'CHAT': {
      const reply = await callBackend('/api/chat', {
        query:    message.query,
        emails:   message.emails,
        history:  message.history,
        userName: message.userName,
      });
      return { success: true, reply: reply.reply };
    }

    case 'DRAFT_REPLY': {
      const result = await callBackend('/api/draft-reply', {
        emailFrom:    message.emailFrom,
        emailSubject: message.emailSubject,
        emailSnippet: message.emailSnippet,
        userName:     message.userName,
      });
      return { success: true, draft: result.draft };
    }

    case 'SUMMARIZE': {
      const result = await callBackend('/api/summarize', {
        emails: message.emails,
      });
      return { success: true, summary: result.summary };
    }

    case 'SIGN_OUT': {
      await chrome.storage.local.clear();
      return { success: true };
    }

    default:
      throw new Error(`Unknown message type: ${message.type}`);
  }
}

// ── Google OAuth ──────────────────────────────────────────────────────
async function authenticate() {
  const redirectUri = chrome.identity.getRedirectURL();
  const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  authUrl.searchParams.set('client_id',     CLIENT_ID);
  authUrl.searchParams.set('response_type', 'token');
  authUrl.searchParams.set('redirect_uri',  redirectUri);
  authUrl.searchParams.set('scope',         SCOPES);
  authUrl.searchParams.set('prompt',        'consent');

  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow({ url: authUrl.toString(), interactive: true }, (responseUrl) => {
      if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
      if (!responseUrl)             return reject(new Error('Auth cancelled'));
      const params = new URLSearchParams(new URL(responseUrl).hash.slice(1));
      const token  = params.get('access_token');
      if (!token) return reject(new Error('No token received'));
      resolve(token);
    });
  });
}

async function getUserInfo(token) {
  const res = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

// ── Gmail API ─────────────────────────────────────────────────────────
async function fetchEmails(token, maxResults = 50) {
  const listRes = await fetch(
    `https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=${maxResults}&labelIds=INBOX`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const list     = await listRes.json();
  const messages = (list.messages || []).slice(0, 40);

  const emails = await Promise.all(messages.map(m => fetchEmailDetail(token, m.id)));
  return emails.filter(Boolean);
}

async function fetchEmailDetail(token, id) {
  try {
    const res  = await fetch(
      `https://www.googleapis.com/gmail/v1/users/me/messages/${id}?format=metadata&metadataHeaders=From,Subject,Date`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await res.json();
    const h    = (name) => (data.payload?.headers || []).find(h => h.name === name)?.value || '';
    return { id: data.id, from: h('From'), subject: h('Subject'), date: h('Date'), snippet: data.snippet || '' };
  } catch {
    return null;
  }
}

// ── Backend API ───────────────────────────────────────────────────────
async function callBackend(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Backend error: ${res.status}`);
  return res.json();
}
