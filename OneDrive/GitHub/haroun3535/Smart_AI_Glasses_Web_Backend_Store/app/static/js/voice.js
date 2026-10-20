const messageInput = document.getElementById('message');
const sendButton = document.getElementById('sendMessage');
const recordButton = document.getElementById('recordButton');
const answerBox = document.getElementById('answerBox');
const voiceStatus = document.getElementById('voiceStatus');
const voiceOrb = document.getElementById('voiceOrb');
let mediaRecorder = null;
let mediaStream = null;
let chunks = [];
let currentAudio = null;

function setBusy(busy, message) {
  sendButton.disabled = busy;
  recordButton.disabled = busy && !mediaRecorder;
  voiceOrb.classList.toggle('active', busy);
  voiceStatus.textContent = message;
}

function browserSpeak(text, language) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = {ar:'ar-SA', en:'en-US', fr:'fr-FR', rw:'rw-RW'}[language] || language;
  utterance.rate = 0.95;
  speechSynthesis.speak(utterance);
}

async function speak(text) {
  const language = document.getElementById('language').value;
  const voice = document.getElementById('voice').value;
  try {
    const response = await apiFetch('/api/voice/speak', {
      method: 'POST', body: JSON.stringify({text, voice})
    });
    const blob = await response.blob();
    currentAudio?.pause();
    currentAudio = new Audio(URL.createObjectURL(blob));
    await currentAudio.play();
  } catch (_) {
    browserSpeak(text, language);
    showToast('تم استخدام صوت المتصفح الاحتياطي.', 'info');
  }
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return showToast('اكتب رسالة أولًا.', 'danger');
  setBusy(true, 'المساعد يفكر...');
  try {
    const response = await apiFetch('/api/assistant/chat', {
      method: 'POST', body: JSON.stringify({message, language: document.getElementById('language').value})
    });
    const data = await response.json();
    answerBox.innerHTML = `<strong>AI</strong><p>${escapeHtml(data.reply)}</p>`;
    await speak(data.reply);
    voiceStatus.textContent = 'تم الرد وتشغيل الصوت.';
  } catch (error) {
    showToast(error.message, 'danger');
    voiceStatus.textContent = 'تعذر إكمال الطلب.';
  } finally { setBusy(false, voiceStatus.textContent); }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML.replace(/\n/g, '<br>');
}

async function toggleRecording() {
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) return showToast('الميكروفون غير مدعوم في هذا السياق.', 'danger');
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({audio: true});
    chunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    mediaRecorder.onstop = async () => {
      recordButton.textContent = '🎤 تسجيل مباشر';
      mediaStream.getTracks().forEach(track => track.stop());
      const blob = new Blob(chunks, {type: mediaRecorder.mimeType || 'audio/webm'});
      const form = new FormData();
      form.append('audio', blob, 'voice.webm');
      setBusy(true, 'جاري تحويل الصوت إلى نص...');
      try {
        const response = await apiFetch('/api/voice/transcribe', {method: 'POST', body: form});
        const data = await response.json();
        messageInput.value = data.text;
        await sendMessage();
      } catch (error) {
        showToast(error.message, 'danger');
        setBusy(false, 'تعذر تفريغ الصوت. يمكنك الكتابة بدلًا منه.');
      }
    };
    mediaRecorder.start();
    recordButton.textContent = '■ إيقاف وإرسال';
    voiceStatus.textContent = 'جاري التسجيل...';
    voiceOrb.classList.add('active');
  } catch (error) { showToast(`تعذر فتح الميكروفون: ${error.message}`, 'danger'); }
}

sendButton?.addEventListener('click', sendMessage);
recordButton?.addEventListener('click', toggleRecording);
document.getElementById('stopAudio')?.addEventListener('click', () => {
  currentAudio?.pause();
  speechSynthesis?.cancel();
  if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
});
messageInput?.addEventListener('keydown', event => {
  if (event.ctrlKey && event.key === 'Enter') sendMessage();
});
