// ── Config ────────────────────────────────────────────────────────────
const CLIENT_ID   = '486540453340-0sufvj4rtse805s7e3h7v4kmdumdq7sf.apps.googleusercontent.com';
const BACKEND_URL = 'https://email-cleaner-ai.onrender.com';
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
      if (!token) return { success: false, error: 'TOKEN_EXPIRED' };
      try {
        const emails = await fetchEmails(token);
        return { success: true, emails };
      } catch (err) {
        if (err.message === 'TOKEN_EXPIRED') {
          await chrome.storage.local.clear();
          return { success: false, error: 'TOKEN_EXPIRED' };
        }
        return { success: false, error: err.message };
      }
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

    case 'SEARCH_EMAILS': {
      const { token: searchToken } = await chrome.storage.local.get('token');
      if (!searchToken) throw new Error('Not authenticated');
      const { emails: found, gmailQuery } = await searchEmails(searchToken, message.query);
      return { success: true, emails: found, gmailQuery };
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
async function fetchEmails(token) {
  const queries = [
    'in:inbox',
    'in:inbox category:promotions',
    'in:inbox category:social',
    'in:inbox category:updates',
  ];

  let allMessages = [];

  // Check token validity first with a single fast request
  const testRes = await fetch(
    `https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=1&labelIds=INBOX`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (testRes.status === 401) throw new Error('TOKEN_EXPIRED');

  try {
    const results = await Promise.all(queries.map(q =>
      fetch(`https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=25&q=${encodeURIComponent(q)}`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then(r => r.json()).then(d => d.messages || []).catch(() => [])
    ));

    const seen = new Set();
    for (const batch of results) {
      for (const m of batch) {
        if (!seen.has(m.id)) { seen.add(m.id); allMessages.push(m); }
      }
    }
  } catch (_) {}

  // Fallback: simple inbox fetch if queries returned nothing
  if (allMessages.length === 0) {
    const res = await fetch(
      `https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=50&labelIds=INBOX`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.status === 401) throw new Error('TOKEN_EXPIRED');
    const data = await res.json();
    allMessages = data.messages || [];
  }

  const emails = await Promise.all(allMessages.slice(0, 80).map(m => fetchEmailDetail(token, m.id)));
  return emails.filter(Boolean);
}

async function fetchEmailDetail(token, id, includeBody = false) {
  try {
    const url = includeBody
      ? `https://www.googleapis.com/gmail/v1/users/me/messages/${id}?format=full`
      : `https://www.googleapis.com/gmail/v1/users/me/messages/${id}?format=metadata&metadataHeaders=From,Subject,Date`;
    const res  = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    const data = await res.json();
    const h    = (name) => (data.payload?.headers || []).find(h => h.name === name)?.value || '';
    const body = includeBody ? extractTextBody(data.payload) : '';
    return {
      id:      data.id,
      from:    h('From'),
      subject: h('Subject'),
      date:    h('Date'),
      snippet: body || data.snippet || '',
    };
  } catch {
    return null;
  }
}

function extractTextBody(payload) {
  if (!payload) return '';
  const decode = (data) => {
    try { return atob(data.replace(/-/g,'+').replace(/_/g,'/')); } catch { return ''; }
  };
  if (payload.body?.data) return decode(payload.body.data).slice(0, 600);
  if (payload.parts) {
    for (const part of payload.parts) {
      if (part.mimeType === 'text/plain' && part.body?.data)
        return decode(part.body.data).slice(0, 600);
    }
    for (const part of payload.parts) {
      const r = extractTextBody(part);
      if (r) return r;
    }
  }
  return '';
}

// ── Smart Gmail Query Builder ─────────────────────────────────────────
function buildGmailQuery(userQuery) {
  const q = userQuery.toLowerCase();
  const parts = [];
  const now = new Date();

  // ── Time-based filters (check FIRST, most specific) ──
  const last24  = q.match(/last\s+24\s+hours?/);
  const lastNH  = q.match(/last\s+(\d+)\s+hours?/);
  const lastND  = q.match(/last\s+(\d+)\s+days?/);
  const lastW   = q.match(/last\s+week/);
  const lastM   = q.match(/last\s+month/);
  const todayM  = q.includes('today');
  const yesterM = q.includes('yesterday');

  if (last24 || (lastNH && parseInt(lastNH[1]) <= 24)) {
    parts.push('newer_than:1d');
  } else if (lastNH) {
    const h = parseInt(lastNH[1]);
    const d = Math.ceil(h / 24);
    parts.push(`newer_than:${d}d`);
  } else if (lastND) {
    parts.push(`newer_than:${parseInt(lastND[1])}d`);
  } else if (lastW) {
    parts.push('newer_than:7d');
  } else if (lastM) {
    parts.push('newer_than:30d');
  } else if (todayM) {
    parts.push(`after:${fmt(now)} before:${fmt(new Date(now.getTime() + 86400000))}`);
  } else if (yesterM) {
    parts.push(`after:${fmt(new Date(now.getTime() - 86400000))} before:${fmt(now)}`);
  } else {
    // Match specific dates: "27th", "june 27", "27 june", "27/6"
    const monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
    let day = null, month = now.getMonth(), year = now.getFullYear(), monthFound = false;

    for (let i = 0; i < monthNames.length; i++) {
      if (q.includes(monthNames[i])) { month = i; monthFound = true; break; }
    }
    const yearMatch = q.match(/\b(202\d)\b/);
    if (yearMatch) year = parseInt(yearMatch[1]);

    // avoid matching hour/minute numbers as day
    const dayMatch = q.match(/\b([1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\b/);
    if (dayMatch) day = parseInt(dayMatch[1]);

    if (day) {
      const from = new Date(year, month, day);
      const to   = new Date(year, month, day + 1);
      parts.push(`after:${fmt(from)} before:${fmt(to)}`);
    }
  }

  // ── Sender parsing ──
  const fromPats = [
    /\bfrom\s+([a-zA-Z0-9._-]+)/,
    /e-?mails?\s+(?:from|by|sent\s+by)\s+([a-zA-Z0-9._-]+)/,
    /(?:sent|received)\s+(?:from|by)\s+([a-zA-Z0-9._-]+)/,
    /([a-zA-Z0-9._-]+)(?:'s?)?\s+e?-?mails?/,
  ];
  for (const pat of fromPats) {
    const m = q.match(pat);
    if (m && m[1].length > 2 && !['the','any','all','my','last','this'].includes(m[1])) {
      parts.push(`from:${m[1]}`);
      break;
    }
  }

  // ── Flags ──
  if (q.includes('unread'))                              parts.push('is:unread');
  if (q.match(/attach(ment|ed)/))                        parts.push('has:attachment');
  if (q.includes('starred'))                             parts.push('is:starred');
  if (q.includes('important'))                           parts.push('is:important');
  if (q.includes('spam'))                                parts.push('in:spam');
  if (q.match(/promo(tion)?s?/))                         parts.push('category:promotions');
  if (q.includes('social'))                              parts.push('category:social');
  if (q.includes('unsubscribe') || q.includes('newsletter')) parts.push('category:promotions');

  // ── Subject keyword ──
  const subjM = q.match(/subject[:\s]+["']?([^"'?]+)["']?/);
  if (subjM) parts.push(`subject:(${subjM[1].trim()})`);

  return parts.length > 0 ? parts.join(' ') : userQuery;
}

function fmt(date) {
  return `${date.getFullYear()}/${String(date.getMonth()+1).padStart(2,'0')}/${String(date.getDate()).padStart(2,'0')}`;
}

// ── Smart default query for common questions ──────────────────────────
function getSmartQuery(userQuery) {
  const q = userQuery.toLowerCase();
  if (q.match(/needs?\s+repl|which\s+email.*reply|reply\s+needed/))
    return { query: 'is:unread -category:promotions -from:noreply -from:no-reply', smart: true };
  if (q.match(/unread/))
    return { query: 'is:unread', smart: true };
  if (q.match(/latest|newest|last\s+email|most\s+recent/))
    return { query: 'in:inbox', smart: true };
  if (q.match(/important/))
    return { query: 'is:important', smart: true };
  if (q.match(/attach/))
    return { query: 'has:attachment in:inbox', smart: true };
  if (q.match(/starred/))
    return { query: 'is:starred', smart: true };
  return { query: buildGmailQuery(userQuery), smart: false };
}

// ── Gmail Search ──────────────────────────────────────────────────────
async function searchEmails(token, query) {
  const { query: gmailQuery, smart } = getSmartQuery(query);
  const builtQuery = smart ? gmailQuery : buildGmailQuery(query);
  const finalQuery = builtQuery !== query ? builtQuery : gmailQuery;

  const res = await fetch(
    `https://www.googleapis.com/gmail/v1/users/me/messages?maxResults=20&q=${encodeURIComponent(finalQuery)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const list = await res.json();
  const messages = (list.messages || []).slice(0, 20);
  // Fetch full body for search results so AI has complete context
  const emails = await Promise.all(messages.map(m => fetchEmailDetail(token, m.id, true)));
  return { emails: emails.filter(Boolean), gmailQuery: finalQuery };
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
