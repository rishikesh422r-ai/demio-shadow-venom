const $ = (id) => document.getElementById(id);
const messagesEl = $("messages");
const input = $("messageInput");
const form = $("chatForm");
const micBtn = $("micBtn");
const stage = $("avatarStage");
const stateText = $("characterState");
const statusText = $("statusText");
let history = [];
let recognition = null;
let isListening = false;
let deferredInstall = null;

function setState(state, label) {
  stage.dataset.state = state;
  stateText.textContent = label;
  statusText.textContent = state === "listening" ? "LISTENING" :
    state === "thinking" ? "THINKING" :
    state === "speaking" ? "SPEAKING" : "SYSTEM ONLINE";
}
function addMessage(role, text) {
  const row = document.createElement("div");
  row.className = `message ${role === "user" ? "user-message" : "bot-message"}`;
  if (role !== "user") {
    const avatar = document.createElement("div");
    avatar.className = "mini-avatar";
    avatar.textContent = "D";
    row.appendChild(avatar);
  }
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (role !== "user") {
    const speaker = document.createElement("span");
    speaker.className = "speaker";
    speaker.textContent = "DEMIO ";
    const small = document.createElement("small");
    small.textContent = "• SHADOW VENOM";
    speaker.appendChild(small);
    bubble.appendChild(speaker);
  }
  const p = document.createElement("p");
  p.textContent = text;
  bubble.appendChild(p);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function speak(text) {
  if (!("speechSynthesis" in window)) {
    setState("idle", "Reply ready");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.96;
  utterance.pitch = 0.82;
  utterance.volume = 1;
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v => /en-IN|en-US|en-GB/i.test(v.lang) && /Google|Microsoft|English/i.test(v.name))
    || voices.find(v => /en/i.test(v.lang));
  if (preferred) utterance.voice = preferred;
  utterance.onstart = () => setState("speaking", "Speaking to you");
  utterance.onend = () => setState("idle", "Ready for your next message");
  utterance.onerror = () => setState("idle", "Reply ready");
  window.speechSynthesis.speak(utterance);
}
async function sendMessage(rawText) {
  const message = rawText.trim();
  if (!message) return;
  input.value = "";
  input.style.height = "auto";
  addMessage("user", message);
  setState("thinking", "Thinking about your message");
  $("sendBtn").disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message, history})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The server could not answer.");
    const reply = data.reply || "Sorry, I couldn't make a reply.";
    history.push({role: "user", content: message}, {role: "assistant", content: reply});
    history = history.slice(-12);
    addMessage("assistant", reply);
    speak(reply);
  } catch (error) {
    addMessage("assistant", `Connection issue: ${error.message}`);
    setState("idle", "Connection needs attention");
  } finally {
    $("sendBtn").disabled = false;
  }
}
form.addEventListener("submit", e => { e.preventDefault(); sendMessage(input.value); });
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 110) + "px";
});
input.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
});
document.querySelectorAll("[data-prompt]").forEach(btn => btn.addEventListener("click", () => sendMessage(btn.dataset.prompt)));
$("clearBtn").addEventListener("click", () => {
  history = [];
  window.speechSynthesis?.cancel();
  messagesEl.replaceChildren();
  addMessage("assistant", "Fresh session, bro. What shall we work on?");
  setState("idle", "Awaiting your voice");
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.onstart = () => { isListening = true; micBtn.classList.add("listening"); setState("listening", "Listening to you"); };
  recognition.onresult = event => {
    const heard = event.results[0][0].transcript;
    input.value = heard;
    sendMessage(heard);
  };
  recognition.onerror = event => {
    addMessage("assistant", event.error === "not-allowed"
      ? "Please allow microphone access in your browser settings, then try again."
      : "I couldn't hear that clearly. Tap the microphone and try again.");
    setState("idle", "Ready for your voice");
  };
  recognition.onend = () => { isListening = false; micBtn.classList.remove("listening"); if (stage.dataset.state === "listening") setState("idle", "Ready for your next message"); };
  micBtn.addEventListener("click", () => {
    if (isListening) recognition.stop();
    else { window.speechSynthesis?.cancel(); try { recognition.start(); } catch (_) {} }
  });
} else {
  micBtn.addEventListener("click", () => addMessage("assistant", "Voice input isn't supported in this browser. Open DEMIO in Google Chrome, preferably over HTTPS."));
  micBtn.title = "Voice input requires a supported browser";
}
window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  deferredInstall = event;
  $("installBtn").classList.remove("hidden");
});
$("installBtn").addEventListener("click", async () => {
  if (!deferredInstall) return;
  deferredInstall.prompt();
  await deferredInstall.userChoice;
  deferredInstall = null;
  $("installBtn").classList.add("hidden");
});
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/static/sw.js").catch(() => {}));
}
