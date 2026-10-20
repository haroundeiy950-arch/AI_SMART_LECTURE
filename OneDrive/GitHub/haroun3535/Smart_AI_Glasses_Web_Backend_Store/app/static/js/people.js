const personVideo = document.getElementById('personVideo');
const personCanvas = document.getElementById('personCanvas');
const personPreview = document.getElementById('personPreview');
const captureButton = document.getElementById('capturePerson');
let personStream = null;
let capturedPhoto = '';

document.getElementById('openPersonCamera')?.addEventListener('click', async () => {
  try {
    personStream = await navigator.mediaDevices.getUserMedia({video:true, audio:false});
    personVideo.srcObject = personStream; captureButton.disabled = false;
  } catch (error) { showToast(`تعذر فتح الكاميرا: ${error.message}`, 'danger'); }
});

captureButton?.addEventListener('click', () => {
  if (!personVideo.videoWidth) return;
  personCanvas.width = personVideo.videoWidth; personCanvas.height = personVideo.videoHeight;
  personCanvas.getContext('2d').drawImage(personVideo, 0, 0);
  capturedPhoto = personCanvas.toDataURL('image/jpeg', .85);
  personPreview.src = capturedPhoto; personPreview.hidden = false; personVideo.hidden = true;
  personStream?.getTracks().forEach(track => track.stop());
  showToast('تم التقاط الصورة.', 'success');
});

document.getElementById('personForm')?.addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await apiFetch('/api/people', {method:'POST', body:JSON.stringify({
      code: document.getElementById('personCode').value,
      full_name: document.getElementById('personName').value,
      department: document.getElementById('personDepartment').value,
      notes: document.getElementById('personNotes').value,
      photo: capturedPhoto
    })});
    showToast('تم تسجيل الشخص بنجاح.', 'success');
    setTimeout(() => location.reload(), 700);
  } catch (error) { showToast(error.message, 'danger'); }
});

document.querySelectorAll('.delete-person').forEach(button => button.addEventListener('click', async () => {
  if (!confirm('هل تريد حذف هذا الشخص؟')) return;
  try {
    await apiFetch(`/api/people/${button.dataset.id}`, {method:'DELETE'});
    location.reload();
  } catch (error) { showToast(error.message, 'danger'); }
}));

async function ensurePersonCamera() {
  if (personStream?.active) return;
  personStream = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:960},height:{ideal:720}}, audio:false});
  personVideo.hidden = false; personPreview.hidden = true; personVideo.srcObject = personStream;
  await new Promise(resolve => personVideo.onloadedmetadata = () => resolve());
}

document.querySelectorAll('.collect-samples').forEach(button => button.addEventListener('click', async () => {
  button.disabled = true;
  try {
    await ensurePersonCamera();
    for (let index = 1; index <= 20; index++) {
      personCanvas.width = personVideo.videoWidth; personCanvas.height = personVideo.videoHeight;
      personCanvas.getContext('2d').drawImage(personVideo, 0, 0);
      const image = personCanvas.toDataURL('image/jpeg', .86);
      button.textContent = `العينة ${index}/20`;
      await apiFetch(`/api/people/${button.dataset.id}/samples`, {
        method:'POST', body:JSON.stringify({image})
      });
      await new Promise(resolve => setTimeout(resolve, 220));
    }
    showToast('تم حفظ 20 عينة. اضغط تدريب نموذج الوجه.', 'success');
  } catch (error) { showToast(error.message, 'danger'); }
  finally {
    button.disabled = false; button.textContent = 'التقاط 20 صورة';
    personStream?.getTracks().forEach(track => track.stop()); personStream = null;
  }
}));

document.getElementById('trainFaceModel')?.addEventListener('click', async event => {
  const button = event.currentTarget; button.disabled = true; button.textContent = 'جاري التدريب...';
  try {
    const response = await apiFetch('/api/faces/train', {method:'POST'});
    const data = await response.json();
    showToast(`تم التدريب: ${data.people} أشخاص و${data.samples} عينة.`, 'success');
  } catch (error) { showToast(error.message, 'danger'); }
  finally { button.disabled = false; button.textContent = 'تدريب نموذج الوجه'; }
});
