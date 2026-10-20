const el = document.querySelector('#live-room-config');
const cfg = {api: el.dataset.api, signals: el.dataset.signals, recording: el.dataset.recording,
  csrf: el.dataset.csrf, userId: Number(el.dataset.userId), lecturer: el.dataset.lecturer === 'true'};
const canvas = document.querySelector('#board');
const localVideo = document.querySelector('#local-camera');
const remoteVideo = document.querySelector('#remote-camera');
let boardChanged = false, mediaStream = null, signalCursor = 0, recognition = null;
let mediaRecorder = null, recordedChunks = [], recordingStarted = 0;
const peers = new Map();

async function jsonApi(url, data) {
  const options = data ? {method:'POST', headers:{'X-CSRFToken':cfg.csrf,'Content-Type':'application/json'}, body:JSON.stringify(data)} : {};
  const response = await fetch(url, options);
  if (response.status === 404) { location.href='/dashboard/'; return null; }
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed');
  return body;
}
function escapeHtml(value) { const node=document.createElement('div'); node.textContent=value; return node.innerHTML; }

if (canvas) {
  const ctx=canvas.getContext('2d'); let drawing=false, last=null, erasing=false;
  const point=e=>{const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height}};
  canvas.onpointerdown=e=>{drawing=true;last=point(e);canvas.setPointerCapture(e.pointerId)};
  canvas.onpointermove=e=>{if(!drawing)return;const p=point(e);ctx.beginPath();ctx.moveTo(last.x,last.y);ctx.lineTo(p.x,p.y);
    ctx.lineWidth=document.querySelector('#width').value;ctx.lineCap='round';ctx.strokeStyle=erasing?'#fff':document.querySelector('#color').value;ctx.stroke();last=p;boardChanged=true};
  canvas.onpointerup=()=>drawing=false;
  document.querySelector('#eraser').onclick=()=>{erasing=!erasing;document.querySelector('#eraser').textContent=erasing?'Pen':'Eraser'};
  document.querySelector('#clear').onclick=()=>{ctx.clearRect(0,0,canvas.width,canvas.height);boardChanged=true};
  document.querySelector('#network-diagram').onclick=()=>{
    ctx.clearRect(0,0,canvas.width,canvas.height);ctx.font='bold 25px sans-serif';ctx.textAlign='center';ctx.lineWidth=3;
    const items=[['PC',150],['Switch',410],['Router',690],['Server',950]], y=300;
    items.forEach(([label,x],i)=>{ctx.fillStyle='#eef0ff';ctx.strokeStyle='#5b5ce2';ctx.fillRect(x-70,y-38,140,76);ctx.strokeRect(x-70,y-38,140,76);
      ctx.fillStyle='#101827';ctx.fillText(label,x,y+8);if(i<items.length-1){const next=items[i+1][1];ctx.beginPath();ctx.moveTo(x+70,y);ctx.lineTo(next-80,y);ctx.stroke();
      ctx.beginPath();ctx.moveTo(next-80,y);ctx.lineTo(next-95,y-9);ctx.lineTo(next-95,y+9);ctx.closePath();ctx.fillStyle='#5b5ce2';ctx.fill()}});boardChanged=true};
}

async function startCamera() {
  if (mediaStream) return mediaStream;
  try {
    mediaStream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:true});
    localVideo.srcObject=mediaStream;document.querySelector('#camera-layer').classList.add('active');
    document.querySelector('#permission-message').textContent='Camera and microphone are active.';
    document.querySelector('#camera-toggle').textContent='📷 Stop camera';
    if (cfg.lecturer) for (const id of currentParticipantIds) await createOffer(id);
    return mediaStream;
  } catch(error) { document.querySelector('#permission-message').textContent=`Camera error: ${error.message}. Allow Camera and Microphone in browser settings.`; throw error; }
}
function stopCamera(){if(!mediaStream)return;mediaStream.getTracks().forEach(t=>t.stop());mediaStream=null;localVideo.srcObject=null;
  document.querySelector('#camera-layer').classList.remove('active');document.querySelector('#camera-toggle').textContent='📷 Start camera';}
document.querySelector('#camera-toggle').onclick=()=>mediaStream?stopCamera():startCamera();

const currentParticipantIds=new Set();
function peerFor(remoteId){if(peers.has(remoteId))return peers.get(remoteId);const pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]});
  if(mediaStream)mediaStream.getTracks().forEach(track=>pc.addTrack(track,mediaStream));
  pc.onicecandidate=e=>{if(e.candidate)sendSignal(remoteId,'ice',e.candidate.toJSON())};
  pc.ontrack=e=>{remoteVideo.srcObject=e.streams[0];document.querySelector('#camera-layer').classList.add('active')};peers.set(remoteId,pc);return pc;}
async function sendSignal(target,type,payload){return jsonApi(cfg.signals,{target_user_id:target,signal_type:type,payload})}
async function createOffer(studentId){const pc=peerFor(studentId);if(pc.signalingState!=='stable')return;const offer=await pc.createOffer();await pc.setLocalDescription(offer);await sendSignal(studentId,'offer',offer)}
async function pollSignals(){try{const data=await jsonApi(`${cfg.signals}?after=${signalCursor}`);for(const s of data.signals){signalCursor=Math.max(signalCursor,s.id);const pc=peerFor(s.sender_id);
    if(s.type==='offer'){if(!mediaStream)await startCamera();await pc.setRemoteDescription(s.payload);const answer=await pc.createAnswer();await pc.setLocalDescription(answer);await sendSignal(s.sender_id,'answer',answer)}
    else if(s.type==='answer')await pc.setRemoteDescription(s.payload);else if(s.type==='ice')await pc.addIceCandidate(s.payload)}}catch(error){console.warn('Signal polling:',error.message)}}

function setupSpeech(){const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){document.querySelector('#transcript').textContent='Speech recognition is not supported. Use Microsoft Edge or Google Chrome.';return}
  recognition=new SpeechRecognition();recognition.continuous=true;recognition.interimResults=true;recognition.lang=document.documentElement.lang||'en-US';
  recognition.onresult=e=>{let finalText='',interim='';for(let i=e.resultIndex;i<e.results.length;i++){const text=e.results[i][0].transcript;if(e.results[i].isFinal)finalText+=text;else interim+=text}
    document.querySelector('#live-caption').textContent=interim||finalText;const box=document.querySelector('#transcript');if(finalText){box.textContent+=(box.textContent.startsWith('Press')?'':'\n')+finalText;
      jsonApi(cfg.api,{action:'chat',text:`🎙 ${finalText}`}).catch(()=>{})}};
  recognition.onerror=e=>document.querySelector('#transcript').textContent+=`\nSpeech error: ${e.error}`;}
document.querySelector('#speech-toggle').onclick=()=>{if(!recognition)setupSpeech();if(!recognition)return;if(document.querySelector('#speech-toggle').dataset.active==='true'){
  recognition.stop();document.querySelector('#speech-toggle').dataset.active='false';document.querySelector('#speech-toggle').textContent='🎙 Start speech text'}else{
  recognition.start();document.querySelector('#speech-toggle').dataset.active='true';document.querySelector('#speech-toggle').textContent='⏹ Stop speech text'}};

async function startRecording(){await startCamera();const composite=document.createElement('canvas');composite.width=1100;composite.height=620;const cx=composite.getContext('2d');
  const paint=()=>{cx.fillStyle='#fff';cx.fillRect(0,0,composite.width,composite.height);if(canvas)cx.drawImage(canvas,0,0,composite.width,composite.height);
    if(localVideo.readyState>=2)cx.drawImage(localVideo,composite.width-300,20,280,158);if(mediaRecorder&&mediaRecorder.state==='recording')requestAnimationFrame(paint)};paint();
  const stream=composite.captureStream(25);mediaStream.getAudioTracks().forEach(t=>stream.addTrack(t));recordedChunks=[];mediaRecorder=new MediaRecorder(stream,{mimeType:MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')?'video/webm;codecs=vp9,opus':'video/webm'});
  mediaRecorder.ondataavailable=e=>{if(e.data.size)recordedChunks.push(e.data)};mediaRecorder.onstop=uploadRecording;recordingStarted=Date.now();mediaRecorder.start(1000);
  document.querySelector('#record-toggle').textContent='⏹ Stop & save recording';}
async function uploadRecording(){const blob=new Blob(recordedChunks,{type:'video/webm'});const data=new FormData();data.append('recording',blob,`lecture-${Date.now()}.webm`);data.append('duration',Math.round((Date.now()-recordingStarted)/1000));
  const response=await fetch(cfg.recording,{method:'POST',headers:{'X-CSRFToken':cfg.csrf},body:data});const body=await response.json();
  document.querySelector('#record-toggle').textContent=response.ok?'✓ Saved — record again':`Save failed: ${body.error}`;mediaRecorder=null;}
document.querySelector('#record-toggle')?.addEventListener('click',()=>{if(mediaRecorder&&mediaRecorder.state==='recording')mediaRecorder.stop();else startRecording()});

async function refresh(){try{if(cfg.lecturer&&boardChanged){await jsonApi(cfg.api,{action:'board',image:canvas.toDataURL('image/png')});boardChanged=false}const d=await jsonApi(cfg.api);if(!d)return;
  if(!cfg.lecturer&&d.board)document.querySelector('#live-board').src=d.board;document.querySelector('#count').textContent=`(${d.participants.length+1})`;
  document.querySelector('#participants').innerHTML=`<p>👨‍🏫 ${escapeHtml(d.lecturer)}</p>`+d.participants.map(p=>`<p>${p.hand?'✋':'👨‍🎓'} ${escapeHtml(p.name)}</p>`).join('');
  document.querySelector('#messages').innerHTML=d.messages.map(m=>`<p><b>${escapeHtml(m.name)}</b> ${escapeHtml(m.text)}</p>`).join('');
  if(cfg.lecturer)for(const p of d.participants){if(!currentParticipantIds.has(p.id)){currentParticipantIds.add(p.id);if(mediaStream)await createOffer(p.id)}}}catch(error){console.warn(error.message)}}
document.querySelector('#send-chat').onclick=async()=>{const input=document.querySelector('#chat-text');if(input.value.trim())await jsonApi(cfg.api,{action:'chat',text:input.value});input.value='';refresh()};
document.querySelector('#chat-text').addEventListener('keydown',e=>{if(e.key==='Enter')document.querySelector('#send-chat').click()});
document.querySelector('#raise-hand')?.addEventListener('click',()=>jsonApi(cfg.api,{action:'hand'}).then(refresh));
document.querySelector('#end-live')?.addEventListener('click',async()=>{if(mediaRecorder?.state==='recording')mediaRecorder.stop();await jsonApi(cfg.api,{action:'end'});location.href='/dashboard/'});
refresh();pollSignals();setInterval(refresh,1500);setInterval(pollSignals,1000);
