const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  window.clearTimeout(window.__toastTimer);
  window.__toastTimer = window.setTimeout(() => toast.className = 'toast', 3600);
}

async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set('X-CSRF-Token', csrfToken);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const response = await fetch(url, {...options, headers});
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  }
  return response;
}

const menuButton = document.getElementById('menuButton');
menuButton?.addEventListener('click', () => document.getElementById('sidebar')?.classList.toggle('open'));

window.showToast = showToast;
window.apiFetch = apiFetch;
window.csrfToken = csrfToken;
