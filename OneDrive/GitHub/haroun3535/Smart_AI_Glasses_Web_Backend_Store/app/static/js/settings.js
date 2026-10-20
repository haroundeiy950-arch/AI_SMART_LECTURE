document.getElementById('changePasswordForm')?.addEventListener('submit', async event => {
  event.preventDefault();
  const currentPassword = document.getElementById('currentPassword').value;
  const newPassword = document.getElementById('newPassword').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  if (newPassword !== confirmPassword) return showToast('تأكيد كلمة المرور غير مطابق.', 'danger');
  try {
    await apiFetch('/api/change-password', {method:'POST', body:JSON.stringify({
      current_password: currentPassword, new_password: newPassword
    })});
    event.target.reset();
    showToast('تم تغيير كلمة المرور بنجاح.', 'success');
  } catch (error) { showToast(error.message, 'danger'); }
});
