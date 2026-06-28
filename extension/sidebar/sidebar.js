// ── State ─────────────────────────────────────────────────────────────
let state = {
  userInfo:    null,
  emails:      [],
  chatHistory: [],
  summaryLoaded: false,
  actionsLoaded: false,
};

// ── Boot ──────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const auth = await msg({ type: 'GET_AUTH_STATUS' });
  if (auth.authenticated) {
    state.userInfo = auth.userInfo;
    showApp();
    loadEmails();
  } else {
    showLogin();
  }
  bindEvents();
});

// ── Auth ──────────────────────────────────────────────────────────────
function showLogin() { show('login-screen'); hide('app-screen'); }
function showApp()   { hide('login-screen'); show('app-screen'); }

document.getElementById('connect-btn').addEventListener('click', async () => {
  showOverlay('Connecting to Gmail...');
  const result = await msg({ type: 'AUTH' });
  hideOverlay();
  if (result.success) {
    state.userInfo = result.userInfo;
    showApp();
    loadEmails();
  } else {
    alert('Connection failed. Please try again.');
  }
});

// ── Load Emails ───────────────────────────────────────────────────────
async function loadEmails() {
  document.getElementById('header-user').textContent = state.userInfo?.email || '';
  const countEl = document.getElementById('email-count');
  if (countEl) countEl.textContent = 'Reading inbox...';
  showOverlay('Reading your inbox...');
  const result = await msg({ type: 'FETCH_EMAILS' });
  hideOverlay();
  if (result.success) {
    state.emails = result.emails;
    if (countEl) countEl.textContent = `${result.emails.length} emails loaded`;
    renderSummary();
    renderActions();
  } else if (result.error === 'TOKEN_EXPIRED') {
    if (countEl) { countEl.textContent = 'Session expired'; countEl.style.color = '#f85149'; }
    showReconnectBanner();
  } else {
    if (countEl) countEl.textContent = 'Could not load emails';
  }
}

function showReconnectBanner() {
  const existing = document.getElementById('reconnect-banner');
  if (existing) return;
  const banner = document.createElement('div');
  banner.id = 'reconnect-banner';
  banner.className = 'reconnect-banner';
  banner.innerHTML = `
    <span>⚠️ Session expired</span>
    <button id="reconnect-btn">Reconnect Gmail</button>
  `;
  document.getElementById('app-screen').prepend(banner);
  document.getElementById('reconnect-btn').addEventListener('click', async () => {
    banner.remove();
    showOverlay('Reconnecting...');
    const result = await msg({ type: 'AUTH' });
    hideOverlay();
    if (result.success) {
      state.userInfo = result.userInfo;
      loadEmails();
    }
  });
}

// ── Events ────────────────────────────────────────────────────────────
function bindEvents() {
  // Tabs
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Chat send
  document.getElementById('chat-send').addEventListener('click', sendChat);
  document.getElementById('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });

  // Chat starters
  document.querySelectorAll('.starter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('chat-input').value = btn.dataset.q;
      sendChat();
    });
  });

  // Refresh
  document.getElementById('refresh-btn').addEventListener('click', () => {
    state.summaryLoaded = false;
    state.actionsLoaded = false;
    state.chatHistory   = [];
    loadEmails();
  });

  // Close
  document.getElementById('close-btn').addEventListener('click', () => {
    window.parent.postMessage({ type: 'ECAI_CLOSE_SIDEBAR' }, '*');
  });
}

// ── Tabs ──────────────────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabName));
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `tab-${tabName}`);
    c.classList.toggle('hidden', c.id !== `tab-${tabName}`);
  });
}

// ── Chat ──────────────────────────────────────────────────────────────
async function sendChat() {
  const input = document.getElementById('chat-input');
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  hide('chat-starters');

  appendMessage('user', query);
  state.chatHistory.push({ role: 'user', content: query });

  const thinkingId = appendMessage('ai', '__THINKING__');
  startThinkingAnimation(thinkingId);

  try {
    let chatMode = 'general';
    let chatEmails = [...state.emails];
    let gmailQuery = '';
    let searchCount = 0;

    // Always search Gmail with the user's query
    try {
      const searchResult = await msg({ type: 'SEARCH_EMAILS', query });
      if (searchResult?.success) {
        gmailQuery   = searchResult.gmailQuery || '';
        searchCount  = searchResult.emails?.length || 0;
        // Always use search mode — Gmail's results are more accurate than pre-loaded
        if (gmailQuery) {
          chatMode   = 'search';
          chatEmails = searchResult.emails || [];
        }
      }
    } catch (_) {}

    const result = await msg({
      type:        'CHAT',
      query,
      emails:      chatEmails.slice(0, 80),
      history:     state.chatHistory.slice(-8),
      userName:    state.userInfo?.name || 'there',
      mode:        chatMode,
      gmailQuery,
      searchCount,
    });

    const reply = result?.success ? result.reply : 'Sorry, something went wrong. Please try again.';
    updateMessage(thinkingId, reply);
    state.chatHistory.push({ role: 'assistant', content: reply });
  } catch (err) {
    updateMessage(thinkingId, 'Sorry, something went wrong. Please try again.');
  } finally {
    stopThinkingAnimation();
  }
}

// ── Thinking animation ────────────────────────────────────────
let _thinkingTimer = null;
const THINKING_STEPS = [
  'Thinking',
  'Reading your inbox',
  'Searching emails',
  'Analyzing',
  'Almost there',
];

function startThinkingAnimation(id) {
  let step = 0; let dots = 0;
  const el = document.getElementById(id);
  if (!el) return;
  _thinkingTimer = setInterval(() => {
    dots = (dots + 1) % 4;
    const label = THINKING_STEPS[step % THINKING_STEPS.length];
    const dotStr = '.'.repeat(dots);
    if (el) el.innerHTML = `<div class="thinking-wrap"><span class="thinking-spinner"></span><span class="thinking-label">${label}<span class="thinking-dots">${dotStr}</span></span></div>`;
    if (dots === 3) step++;
  }, 400);
}

function stopThinkingAnimation() {
  if (_thinkingTimer) { clearInterval(_thinkingTimer); _thinkingTimer = null; }
}

function appendMessage(role, text) {
  const id       = `msg-${Date.now()}`;
  const messages = document.getElementById('chat-messages');
  const div      = document.createElement('div');
  div.className  = `${role === 'ai' ? 'ai' : 'user'}-message`;
  if (role === 'ai') {
    const content = text === '__THINKING__'
      ? `<div class="thinking-wrap"><span class="thinking-spinner"></span><span class="thinking-label">Thinking<span class="thinking-dots">...</span></span></div>`
      : renderMarkdown(text);
    div.innerHTML = `<div class="ai-avatar"><svg width="14" height="14" viewBox="0 0 36 36" fill="none"><rect x="4" y="9" width="28" height="20" rx="4" stroke="white" stroke-width="3" fill="none"/><path d="M4 13l14 9 14-9" stroke="white" stroke-width="3" stroke-linecap="round"/></svg></div><div class="message-bubble ai" id="${id}">${content}</div>`;
  } else {
    div.innerHTML = `<div class="message-bubble user" id="${id}">${escapeHtml(text)}</div>`;
  }
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

function updateMessage(id, text) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = renderMarkdown(text);
  document.getElementById('chat-messages').scrollTop = 99999;
}

// ── Summary ───────────────────────────────────────────────────────────
function renderSummary() {
  const emails   = state.emails;
  const cats     = { Important: 0, Promotions: 0, Spam: 0, Other: 0 };
  const keywords = {
    Important:  ['invoice', 'payment', 'receipt', 'otp', 'verify', 'bank', 'urgent', 'job', 'offer', 'interview', 'meeting', 'appointment', 'order', 'shipped', 'booking'],
    Promotions: ['sale', '% off', 'discount', 'deal', 'offer', 'promo', 'newsletter', 'unsubscribe', 'coupon'],
    Spam:       ['won', 'winner', 'lottery', 'prize', 'click here', 'earn money', 'free gift', 'guaranteed'],
  };

  emails.forEach(e => {
    const text = `${e.subject} ${e.snippet}`.toLowerCase();
    if (keywords.Spam.some(k => text.includes(k)))       cats.Spam++;
    else if (keywords.Important.some(k => text.includes(k))) cats.Important++;
    else if (keywords.Promotions.some(k => text.includes(k))) cats.Promotions++;
    else cats.Other++;
  });

  const important = emails.filter(e => {
    const t = `${e.subject} ${e.snippet}`.toLowerCase();
    return keywords.Important.some(k => t.includes(k));
  }).slice(0, 5);

  const html = `
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-num" style="color:#059669">${cats.Important}</div><div class="stat-label">Important</div></div>
      <div class="stat-card"><div class="stat-num" style="color:#d97706">${cats.Promotions}</div><div class="stat-label">Promotions</div></div>
      <div class="stat-card"><div class="stat-num" style="color:#dc2626">${cats.Spam}</div><div class="stat-label">Spam</div></div>
      <div class="stat-card"><div class="stat-num" style="color:#6b7280">${cats.Other}</div><div class="stat-label">Other</div></div>
    </div>
    <div class="section-title">📬 Recent Important Emails</div>
    ${important.length ? important.map(e => `
      <div class="email-item">
        <div class="from">${escapeHtml(e.from.split('<')[0].trim() || e.from)}</div>
        <div class="subject">${escapeHtml(e.subject)}</div>
        <div class="snippet">${escapeHtml(e.snippet)}</div>
      </div>
    `).join('') : '<p style="color:#9ca3af;font-size:0.85rem;padding:0.5rem 0">No important emails found.</p>'}
    <div class="section-title" style="margin-top:0.5rem">📊 Total scanned: ${emails.length} emails</div>
  `;

  document.getElementById('summary-content').innerHTML = html;
  state.summaryLoaded = true;
}

// ── Actions ───────────────────────────────────────────────────────────
function renderActions() {
  const emails    = state.emails;
  const replyKw   = ['can you', 'please', 'kindly', 'let me know', 'waiting', 'confirm', 'response', 'reply', 'invitation', 'interview', 'meeting', 'schedule', 'attend'];
  const urgentKw  = ['urgent', 'asap', 'immediately', 'today', 'deadline', 'expires', 'otp', 'verification', 'action required', 'due'];
  const promoKw   = ['unsubscribe', 'newsletter', 'no-reply', 'noreply', 'marketing', 'offers', 'deals', 'sale'];

  const needsReply  = emails.filter(e => replyKw.some(k => `${e.subject} ${e.snippet}`.toLowerCase().includes(k))).slice(0, 5);
  const urgent      = emails.filter(e => urgentKw.some(k => `${e.subject} ${e.snippet}`.toLowerCase().includes(k))).slice(0, 5);
  const promotions  = emails.filter(e => promoKw.some(k => `${e.from} ${e.subject}`.toLowerCase().includes(k))).slice(0, 5);

  const cardHtml = (e, type) => `
    <div class="action-card">
      <h4>${escapeHtml(e.subject || '(No subject)')}</h4>
      <div class="meta">From: ${escapeHtml(e.from.split('<')[0].trim())}</div>
      <div class="action-buttons">
        ${type !== 'promo' ? `<button class="btn-sm btn-draft" onclick="draftReply('${encodeURIComponent(JSON.stringify(e))}')">✍️ Draft Reply</button>` : ''}
        ${type === 'promo' ? `<button class="btn-sm btn-unsub" onclick="copyUnsub('${escapeHtml(e.from)}')">🚫 Copy Unsubscribe</button>` : ''}
      </div>
    </div>
  `;

  const html = `
    ${needsReply.length ? `<div class="section-title">📬 Needs a Reply (${needsReply.length})</div>${needsReply.map(e => cardHtml(e, 'reply')).join('')}` : ''}
    ${urgent.length ? `<div class="section-title">🚨 Urgent (${urgent.length})</div>${urgent.map(e => cardHtml(e, 'urgent')).join('')}` : ''}
    ${promotions.length ? `<div class="section-title">🚫 Unsubscribe Suggestions (${promotions.length})</div>${promotions.map(e => cardHtml(e, 'promo')).join('')}` : ''}
    ${!needsReply.length && !urgent.length && !promotions.length ? '<div class="loading-state"><p>✅ Your inbox looks clean!</p></div>' : ''}
  `;

  document.getElementById('actions-content').innerHTML = html;
  state.actionsLoaded = true;
}

// ── Draft Reply ───────────────────────────────────────────────────────
async function draftReply(encodedEmail) {
  const email = JSON.parse(decodeURIComponent(encodedEmail));
  showOverlay('Drafting your reply...');

  const result = await msg({
    type:         'DRAFT_REPLY',
    emailFrom:    email.from,
    emailSubject: email.subject,
    emailSnippet: email.snippet,
    userName:     state.userInfo?.name || 'there',
  });

  hideOverlay();
  if (result.success) showDraftModal(result.draft, email.subject);
  else alert('Could not generate draft. Please try again.');
}

function showDraftModal(draft, subject) {
  const modal = document.createElement('div');
  modal.className = 'draft-modal';
  modal.innerHTML = `
    <div class="draft-modal-content">
      <h4>✍️ Draft Reply — ${escapeHtml(subject)}</h4>
      <textarea class="draft-textarea">${escapeHtml(draft)}</textarea>
      <div class="draft-actions">
        <button class="btn-copy" onclick="copyDraft(this)">📋 Copy to Clipboard</button>
        <button class="btn-close-modal" onclick="this.closest('.draft-modal').remove()">Close</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

function copyDraft(btn) {
  const text = btn.closest('.draft-modal-content').querySelector('.draft-textarea').value;
  navigator.clipboard.writeText(text).then(() => { btn.textContent = '✅ Copied!'; });
}

function copyUnsub(from) {
  navigator.clipboard.writeText(`Please unsubscribe me from your mailing list. From: ${from}`).then(() => {
    alert('Copied! Paste this into a reply to unsubscribe.');
  });
}

// ── Helpers ───────────────────────────────────────────────────────────
function msg(data) {
  return chrome.runtime.sendMessage(data);
}

function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id) { document.getElementById(id)?.classList.add('hidden'); }

function showOverlay(text) {
  document.getElementById('loading-text').textContent = text;
  show('loading-overlay');
}
function hideOverlay() { hide('loading-overlay'); }

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderMarkdown(text) {
  if (!text) return '';

  const lines = text.split('\n');
  const out = [];
  let inList = false;
  let listType = null;

  const closeList = () => {
    if (inList) { out.push(listType === 'ol' ? '</ol>' : '</ul>'); inList = false; listType = null; }
  };

  const inlineFormat = (s) => s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');

  for (let raw of lines) {
    const line = raw.trim();
    if (!line) { closeList(); out.push('<div class="msg-spacer"></div>'); continue; }

    // Numbered list  1. 2. 3.
    const numMatch = line.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      if (!inList || listType !== 'ol') { closeList(); out.push('<ol class="msg-list">'); inList = true; listType = 'ol'; }
      out.push(`<li>${inlineFormat(escapeHtml(numMatch[2]))}</li>`);
      continue;
    }

    // Bullet list  • - *
    const bulMatch = line.match(/^[•\-\*]\s+(.*)/);
    if (bulMatch) {
      if (!inList || listType !== 'ul') { closeList(); out.push('<ul class="msg-list">'); inList = true; listType = 'ul'; }
      out.push(`<li>${inlineFormat(escapeHtml(bulMatch[1]))}</li>`);
      continue;
    }

    // Heading  **Title:**  or  ### Title
    const headMatch = line.match(/^#{1,3}\s+(.*)/);
    if (headMatch) { closeList(); out.push(`<div class="msg-heading">${inlineFormat(escapeHtml(headMatch[1]))}</div>`); continue; }

    closeList();
    out.push(`<p class="msg-para">${inlineFormat(escapeHtml(line))}</p>`);
  }

  closeList();
  return out.join('');
}
