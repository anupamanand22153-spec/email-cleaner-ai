// Injected into mail.google.com — adds the AI assistant sidebar

let sidebarIframe = null;
let toggleBtn     = null;
let isOpen        = false;

function injectSidebar() {
  if (document.getElementById('ecai-sidebar')) return;

  // ── Sidebar iframe ────────────────────────────────────────────────
  sidebarIframe = document.createElement('iframe');
  sidebarIframe.id  = 'ecai-sidebar';
  sidebarIframe.src = chrome.runtime.getURL('sidebar/sidebar.html');
  sidebarIframe.style.cssText = `
    position: fixed;
    top: 0;
    right: -420px;
    width: 400px;
    height: 100vh;
    border: none;
    z-index: 99999;
    box-shadow: -4px 0 24px rgba(0,0,0,0.15);
    transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 0;
    background: #fff;
  `;
  document.body.appendChild(sidebarIframe);

  // ── Toggle button ─────────────────────────────────────────────────
  toggleBtn = document.createElement('button');
  toggleBtn.id = 'ecai-toggle';
  toggleBtn.innerHTML = `
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  `;
  toggleBtn.title = 'Email Cleaner AI';
  toggleBtn.style.cssText = `
    position: fixed;
    right: 16px;
    bottom: 80px;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1E3A8A, #2563EB);
    border: none;
    cursor: pointer;
    z-index: 99998;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 16px rgba(37,99,235,0.4);
    transition: transform 0.2s, box-shadow 0.2s;
  `;
  toggleBtn.addEventListener('mouseenter', () => {
    toggleBtn.style.transform  = 'scale(1.1)';
    toggleBtn.style.boxShadow  = '0 6px 20px rgba(37,99,235,0.5)';
  });
  toggleBtn.addEventListener('mouseleave', () => {
    toggleBtn.style.transform  = 'scale(1)';
    toggleBtn.style.boxShadow  = '0 4px 16px rgba(37,99,235,0.4)';
  });
  toggleBtn.addEventListener('click', toggleSidebar);
  document.body.appendChild(toggleBtn);
}

function toggleSidebar() {
  isOpen = !isOpen;
  if (isOpen) {
    sidebarIframe.style.right = '0px';
    toggleBtn.style.right     = '416px';
  } else {
    sidebarIframe.style.right = '-420px';
    toggleBtn.style.right     = '16px';
  }
}

// Listen for close message from sidebar
window.addEventListener('message', (event) => {
  if (event.data?.type === 'ECAI_CLOSE_SIDEBAR') {
    isOpen = false;
    sidebarIframe.style.right = '-420px';
    toggleBtn.style.right     = '16px';
  }
});

// Inject when Gmail is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectSidebar);
} else {
  injectSidebar();
}

// Re-inject on Gmail navigation (it's a SPA)
const observer = new MutationObserver(() => {
  if (!document.getElementById('ecai-sidebar')) injectSidebar();
});
observer.observe(document.body, { childList: true, subtree: false });
