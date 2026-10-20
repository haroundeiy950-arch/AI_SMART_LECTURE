const video = document.getElementById('cameraVideo');
const canvas = document.getElementById('captureCanvas');
const startButton = document.getElementById('startCamera');
const stopButton = document.getElementById('stopCamera');
const analyzeButton = document.getElementById('analyzeFrame');
const badge = document.getElementById('cameraBadge');
const placeholder = document.getElementById('cameraPlaceholder');
let stream = null;

async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({video: {width:{ideal:1280}, height:{ideal:720}}, audio:false});
    video.srcObject = stream;
    placeholder.hidden = true;
    badge.textContent = 'مباشر'; badge.classList.add('online');
    startButton.disabled = true; stopButton.disabled = false; analyzeButton.disabled = false;
  } catch (error) { showToast(`تعذر فتح الكاميرا: ${error.message}`, 'danger'); }
}

function stopCamera() {
  stream?.getTracks().forEach(track => track.stop());
  stream = null; video.srcObject = null; placeholder.hidden = false;
  badge.textContent = 'متوقفة'; badge.classList.remove('online');
  startButton.disabled = false; stopButton.disabled = true; analyzeButton.disabled = true;
}

async function analyzeFrame() {
  if (!stream || !video.videoWidth) return;
  analyzeButton.disabled = true; analyzeButton.textContent = 'جاري التحليل...';
  canvas.width = video.videoWidth; canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const image = canvas.toDataURL('image/jpeg', 0.82);
  try {
    const response = await apiFetch('/api/camera/analyze', {method:'POST', body:JSON.stringify({image})});
    const data = await response.json();
    document.getElementById('sceneResult').textContent = data.scene || '—';
    document.getElementById('objectsResult').textContent = (data.objects || []).join('، ') || '—';
    document.getElementById('textResult').textContent = data.visible_text || '—';
    document.getElementById('peopleResult').textContent = data.people_count ?? '—';
    const localFaces = data.local_face_recognition || {};
    const faceText = (localFaces.faces || []).map(face => face.known ? `${face.name} (${face.match_percent}%)` : 'Unknown').join('، ');
    document.getElementById('facesResult').textContent = faceText || (localFaces.available === false ? localFaces.reason : 'لم يتم اكتشاف وجه');
    document.getElementById('emotionResult').textContent = data.general_emotion || '—';
    document.getElementById('safetyResult').textContent = (data.safety_alerts || []).join('، ') || 'لا توجد';
    showToast(`تم حفظ اللقطة: ${data.saved_as}`, 'success');
  } catch (error) { showToast(error.message, 'danger'); }
  finally { analyzeButton.disabled = false; analyzeButton.textContent = 'تحليل المشهد'; }
}

startButton?.addEventListener('click', startCamera);
stopButton?.addEventListener('click', stopCamera);
analyzeButton?.addEventListener('click', analyzeFrame);
window.addEventListener('beforeunload', stopCamera);
