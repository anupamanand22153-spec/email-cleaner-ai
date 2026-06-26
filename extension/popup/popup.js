document.addEventListener('DOMContentLoaded', async () => {
  const auth = await chrome.runtime.sendMessage({ type: 'GET_AUTH_STATUS' });

  if (auth.authenticated) {
    document.getElementById('status-text').textContent  = 'Connected';
    document.getElementById('user-email').textContent   = auth.userInfo?.email || '';
    document.getElementById('signed-in').classList.remove('hidden');
  } else {
    document.getElementById('status-text').textContent = 'Not connected';
    document.getElementById('signed-out').classList.remove('hidden');
  }

  document.getElementById('connect-btn')?.addEventListener('click', async () => {
    document.getElementById('status-text').textContent = 'Connecting...';
    const result = await chrome.runtime.sendMessage({ type: 'AUTH' });
    if (result.success) {
      document.getElementById('user-email').textContent = result.userInfo?.email || '';
      document.getElementById('signed-out').classList.add('hidden');
      document.getElementById('signed-in').classList.remove('hidden');
      document.getElementById('status-text').textContent = 'Connected';
    } else {
      document.getElementById('status-text').textContent = 'Connection failed';
    }
  });

  document.getElementById('open-gmail-btn')?.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://mail.google.com' });
  });

  document.getElementById('signout-btn')?.addEventListener('click', async () => {
    await chrome.runtime.sendMessage({ type: 'SIGN_OUT' });
    document.getElementById('signed-in').classList.add('hidden');
    document.getElementById('signed-out').classList.remove('hidden');
    document.getElementById('status-text').textContent = 'Not connected';
  });
});
