document.getElementById('meetingForm')?.addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.submitter; button.disabled = true; button.textContent = 'جاري التحليل...';
  try {
    const response = await apiFetch('/api/meetings', {method:'POST', body:JSON.stringify({
      title: document.getElementById('meetingTitle').value,
      transcript: document.getElementById('meetingTranscript').value
    })});
    const data = await response.json();
    document.getElementById('meetingResult').innerHTML = `<h3>الملخص</h3><p>${escapeText(data.summary)}</p><h3>المهام</h3><pre>${escapeText(data.tasks)}</pre>`;
    showToast('تم حفظ الاجتماع.', 'success');
  } catch (error) { showToast(error.message, 'danger'); }
  finally { button.disabled = false; button.textContent = 'تلخيص واستخراج المهام'; }
});
function escapeText(value) { const div=document.createElement('div'); div.textContent=value||'—'; return div.innerHTML; }
