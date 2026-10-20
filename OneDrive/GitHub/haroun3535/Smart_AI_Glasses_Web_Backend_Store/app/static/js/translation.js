const sourceText = document.getElementById('sourceText');
const translatedText = document.getElementById('translatedText');
const sourceLanguage = document.getElementById('sourceLanguage');
const targetLanguage = document.getElementById('targetLanguage');
const translateButton = document.getElementById('translateButton');
const speakButton = document.getElementById('speakTranslation');
const stopSpeechButton = document.getElementById('stopSpeech');
const voiceNotice = document.getElementById('voiceNotice');

const SPEECH_LOCALES = {
  ar: 'ar-SA',
  en: 'en-US',
  fr: 'fr-FR',
  rw: 'rw-RW',
  sw: 'sw-KE',
  es: 'es-ES',
  de: 'de-DE',
  'zh-CN': 'zh-CN',
  'zh-TW': 'zh-TW',
  tr: 'tr-TR',
  pt: 'pt-BR',
  it: 'it-IT',
  ja: 'ja-JP',
  ko: 'ko-KR',
  ru: 'ru-RU',
  hi: 'hi-IN',
  nl: 'nl-NL',
  pl: 'pl-PL',
  uk: 'uk-UA',
  id: 'id-ID',
  so: 'so-SO',
  am: 'am-ET'
};

function speechLocale(languageCode) {
  return SPEECH_LOCALES[languageCode] || languageCode;
}

function waitForVoices(timeoutMs = 1500) {
  return new Promise(resolve => {
    const existing = speechSynthesis.getVoices();
    if (existing.length) return resolve(existing);

    const timeout = setTimeout(() => resolve(speechSynthesis.getVoices()), timeoutMs);
    speechSynthesis.addEventListener('voiceschanged', () => {
      clearTimeout(timeout);
      resolve(speechSynthesis.getVoices());
    }, {once: true});
  });
}

function findBestVoice(voices, locale) {
  const exact = voices.find(voice => voice.lang.toLowerCase() === locale.toLowerCase());
  if (exact) return exact;

  const base = locale.split('-')[0].toLowerCase();
  return voices.find(voice => voice.lang.toLowerCase().split('-')[0] === base) || null;
}

translateButton?.addEventListener('click', async () => {
  const text = sourceText.value.trim();
  if (!text) return showToast('اكتب نصًا للترجمة.', 'danger');

  translateButton.disabled = true;
  translateButton.textContent = 'جاري الترجمة...';
  translatedText.value = '';

  try {
    const targetCode = targetLanguage.value;
    const response = await apiFetch('/api/translate', {
      method: 'POST',
      body: JSON.stringify({
        text,
        source: sourceLanguage.value,
        target: targetCode
      })
    });

    const data = await response.json();
    translatedText.value = data.translation || '';
    translatedText.dataset.language = data.target || targetCode;
    voiceNotice.textContent = 'تمت الترجمة. اضغط نطق الترجمة لسماعها.';
    showToast('تمت الترجمة بنجاح.', 'success');
  } catch (error) {
    showToast(error.message, 'danger');
  } finally {
    translateButton.disabled = false;
    translateButton.textContent = 'ترجمة ←';
  }
});

speakButton?.addEventListener('click', async () => {
  const text = translatedText.value.trim();
  if (!text) return showToast('ترجم النص أولًا.', 'danger');

  if (!('speechSynthesis' in window)) {
    return showToast('المتصفح لا يدعم النطق الصوتي.', 'danger');
  }

  speechSynthesis.cancel();

  const languageCode = translatedText.dataset.language || targetLanguage.value;
  const locale = speechLocale(languageCode);
  const voices = await waitForVoices();
  const voice = findBestVoice(voices, locale);

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = locale;
  utterance.rate = 0.95;
  utterance.pitch = 1;
  utterance.volume = 1;

  if (voice) {
    utterance.voice = voice;
    voiceNotice.textContent = `الصوت المستخدم: ${voice.name} (${voice.lang})`;
  } else {
    voiceNotice.textContent = `لا يوجد صوت مثبت مطابق لـ ${locale}. سيحاول المتصفح استخدام أقرب صوت متاح.`;
  }

  utterance.onerror = event => {
    showToast(`تعذر تشغيل الصوت: ${event.error || 'خطأ غير معروف'}`, 'danger');
  };

  speechSynthesis.speak(utterance);
});

stopSpeechButton?.addEventListener('click', () => {
  speechSynthesis.cancel();
  voiceNotice.textContent = 'تم إيقاف الصوت.';
});

targetLanguage?.addEventListener('change', () => {
  translatedText.dataset.language = targetLanguage.value;
});
