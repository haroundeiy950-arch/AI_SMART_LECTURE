function base64urlToBuffer(value) {
  const padding = '='.repeat((4 - value.length % 4) % 4);
  const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  return Uint8Array.from(raw, c => c.charCodeAt(0)).buffer;
}

function bufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  bytes.forEach(byte => binary += String.fromCharCode(byte));
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function prepareCreationOptions(options) {
  options.challenge = base64urlToBuffer(options.challenge);
  options.user.id = base64urlToBuffer(options.user.id);
  options.excludeCredentials = (options.excludeCredentials || []).map(item => ({
    ...item, id: base64urlToBuffer(item.id)
  }));
  return options;
}

function prepareRequestOptions(options) {
  options.challenge = base64urlToBuffer(options.challenge);
  options.allowCredentials = (options.allowCredentials || []).map(item => ({
    ...item, id: base64urlToBuffer(item.id)
  }));
  return options;
}

function serializeRegistration(credential) {
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment,
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
      attestationObject: bufferToBase64url(credential.response.attestationObject),
      transports: credential.response.getTransports ? credential.response.getTransports() : []
    }
  };
}

function serializeAuthentication(credential) {
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment,
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
      authenticatorData: bufferToBase64url(credential.response.authenticatorData),
      signature: bufferToBase64url(credential.response.signature),
      userHandle: credential.response.userHandle ? bufferToBase64url(credential.response.userHandle) : null
    }
  };
}

async function registerPasskey() {
  if (!window.PublicKeyCredential) throw new Error('هذا المتصفح لا يدعم WebAuthn. استخدم Chrome أو Edge حديثًا.');
  const optionsResponse = await apiFetch('/api/passkeys/register/options', {method: 'POST'});
  const options = prepareCreationOptions(await optionsResponse.json());
  const credential = await navigator.credentials.create({publicKey: options});
  if (!credential) throw new Error('لم يتم إنشاء Passkey.');
  await apiFetch('/api/passkeys/register/verify', {
    method: 'POST', body: JSON.stringify(serializeRegistration(credential))
  });
  showToast('تم تسجيل Windows Hello بنجاح.', 'success');
  setTimeout(() => location.reload(), 900);
}

async function loginWithPasskey() {
  if (!window.PublicKeyCredential) throw new Error('هذا المتصفح لا يدعم Windows Hello/WebAuthn.');
  const username = document.getElementById('username')?.value.trim();
  if (!username) throw new Error('اكتب اسم المستخدم أولًا.');
  const optionsResponse = await apiFetch('/api/passkeys/login/options', {
    method: 'POST', body: JSON.stringify({username})
  });
  const options = prepareRequestOptions(await optionsResponse.json());
  const credential = await navigator.credentials.get({publicKey: options});
  if (!credential) throw new Error('لم يكتمل التحقق.');
  const result = await apiFetch('/api/passkeys/login/verify', {
    method: 'POST', body: JSON.stringify(serializeAuthentication(credential))
  });
  const data = await result.json();
  location.href = data.redirect || '/dashboard';
}

document.getElementById('registerPasskey')?.addEventListener('click', async () => {
  try { await registerPasskey(); } catch (error) { showToast(error.message, 'danger'); }
});

document.getElementById('passkeyLogin')?.addEventListener('click', async () => {
  try { await loginWithPasskey(); } catch (error) { showToast(error.message, 'danger'); }
});

document.getElementById('togglePassword')?.addEventListener('click', () => {
  const input = document.getElementById('password');
  if (input) input.type = input.type === 'password' ? 'text' : 'password';
});
