const $ = id => document.getElementById(id);
const state = {
  mode: "chat",
  history: [],
  images: [],
  variables: loadVariables(),
  busy: false,
  recognition: null,
  quiz: null,
  adventureStarted: false
};

const titles = {
  chat: "CHAT INTERFACE",
  voice: "SPEAKING MODE",
  variables: "VARIABLE WORKSPACE",
  mentor: "PERSONAL MENTOR",
  exercise: "EXERCISE STUDIO",
  games: "GAMES & PLAY"
};

function loadVariables() {
  try { return JSON.parse(localStorage.getItem("demio_variables") || "{}"); }
  catch { return {}; }
}
function saveVariables() {
  localStorage.setItem("demio_variables", JSON.stringify(state.variables));
}
function setStatus(ok, text, meta) {
  $("statusText").textContent = text;
  $("sysMeta").textContent = meta || "";
  $("statusDot").style.background = ok ? "var(--green)" : "var(--red)";
  $("statusDot").style.boxShadow = ok ? "0 0 12px var(--green)" : "0 0 12px var(--red)";
}
async function checkHealth() {
  try {
    const r = await fetch("/health");
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "Server unavailable");
    setStatus(true, d.ai_configured ? "SYSTEM ONLINE" : "SERVER ONLINE", d.ai_configured ? `Model: ${d.model}` : "Add OPENAI_API_KEY in Render Environment Variables.");
    $("modelLabel").textContent = d.ai_configured ? d.model : "API KEY REQUIRED";
  } catch (e) {
    setStatus(false, "SERVER ERROR", e.message);
    $("modelLabel").textContent = "OFFLINE";
  }
}
function switchPanel(name) {
  document.querySelectorAll(".nav button").forEach(b => b.classList.toggle("active", b.dataset.panel === name));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("active", p.id === `panel-${name}`));
  $("sectionTitle").textContent = titles[name] || "DEMIO";
  state.mode = name === "mentor" || name === "exercise" || name === "games" ? name : "chat";
}
document.querySelectorAll(".nav button").forEach(b => b.addEventListener("click", () => switchPanel(b.dataset.panel)));

function addBubble(role, text, images = []) {
  const log = $("chatLog");
  const empty = log.querySelector(".empty");
  if (empty) empty.remove();
  const bubble = document.createElement("div");
  bubble.className = `msg ${role === "user" ? "user" : "ai"}`;
  const who = document.createElement("span");
  who.className = "who";
  who.textContent = role === "user" ? "YOU" : "DEMIO";
  const body = document.createElement("div");
  body.textContent = text;
  bubble.append(who, body);
  images.forEach(src => {
    const img = document.createElement("img");
    img.src = src;
    img.alt = "User attachment";
    bubble.appendChild(img);
  });
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
  return bubble;
}
function speak(text) {
  if (!$("speakReplies").checked || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN";
  utterance.rate = 1;
  speechSynthesis.speak(utterance);
}
async function askDemio(message, mode = "chat", images = []) {
  if (state.busy) return;
  state.busy = true;
  $("sendChat").disabled = true;
  const typing = addBubble("assistant", "DEMIO is thinking…");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message,
        mode,
        history: state.history,
        variables: state.variables,
        images
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    if (!data.reply) throw new Error("The AI returned an empty response.");
    typing.remove();
    addBubble("assistant", data.reply);
    state.history.push({role: "user", content: message});
    state.history.push({role: "assistant", content: data.reply});
    state.history = state.history.slice(-24);
    speak(data.reply);
    setStatus(true, "SYSTEM ONLINE", "DEMIO response received.");
    return data.reply;
  } catch (e) {
    typing.remove();
    addBubble("assistant", `Error: ${e.message}`);
    setStatus(false, "REQUEST FAILED", e.message);
    return null;
  } finally {
    state.busy = false;
    $("sendChat").disabled = false;
  }
}
async function sendChat() {
  const text = $("chatInput").value.trim();
  if (!text && !state.images.length) return;
  const images = [...state.images];
  addBubble("user", text || "Please inspect this image.", images);
  $("chatInput").value = "";
  $("fileLabel").textContent = "Images up to 5 MB each";
  state.images = [];
  await askDemio(text || "Please inspect and describe the attached image.", "chat", images);
}
$("sendChat").addEventListener("click", sendChat);
$("chatInput").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
$("attachBtn").addEventListener("click", () => $("imageInput").click());
$("imageInput").addEventListener("change", async e => {
  const files = [...e.target.files];
  for (const file of files.slice(0, 3 - state.images.length)) {
    if (!file.type.startsWith("image/")) continue;
    if (file.size > 5 * 1024 * 1024) { alert(`${file.name} is larger than 5 MB.`); continue; }
    const data = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    state.images.push(data);
  }
  $("fileLabel").textContent = state.images.length ? `${state.images.length} image(s) ready` : "Images up to 5 MB each";
  e.target.value = "";
});
$("newChat").addEventListener("click", () => {
  state.history = [];
  $("chatLog").innerHTML = '<div class="empty">New conversation started.<br>What shall we work on?</div>';
  switchPanel("chat");
});

// Variables: persist locally and include in future AI requests.
function renderVariables() {
  const list = $("varList");
  list.innerHTML = "";
  const entries = Object.entries(state.variables);
  if (!entries.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No variables yet. Add your first variable above.";
    list.appendChild(p);
    return;
  }
  entries.forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = "varitem";
    const label = document.createElement("span");
    label.textContent = `${key} = ${value}`;
    const remove = document.createElement("button");
    remove.className = "btn";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => {
      delete state.variables[key];
      saveVariables();
      renderVariables();
    });
    item.append(label, remove);
    list.appendChild(item);
  });
}
$("addVar").addEventListener("click", () => {
  const key = $("varName").value.trim();
  const value = $("varValue").value.trim();
  if (!key || !value) { alert("Enter both a variable name and value."); return; }
  state.variables[key] = value;
  saveVariables();
  $("varName").value = "";
  $("varValue").value = "";
  renderVariables();
});
renderVariables();

// Mentor and exercise modes route their prompts through the same backend.
$("startMentor").addEventListener("click", async () => {
  const topic = $("mentorTopic").value.trim();
  const level = $("mentorLevel").value;
  if (!topic) { alert("Enter a topic first."); return; }
  switchPanel("chat");
  await askDemio(`Start a mentoring session on ${topic}. My level is ${level}. Teach me one step at a time, give a small example, then ask me one question.`, "mentor");
});
$("makeExercise").addEventListener("click", async () => {
  const topic = $("exerciseTopic").value.trim();
  if (!topic) { alert("Enter a subject first."); return; }
  const level = $("exerciseLevel").value;
  const count = $("exerciseCount").value;
  switchPanel("chat");
  await askDemio(`Create ${count} ${level.toLowerCase()} practice exercises about ${topic}. Number them, give clear instructions and one hint each. Put answers in a separate section labelled "Solutions (open only when ready)" at the end.`, "exercise");
});

// Browser speech recognition is permission-based and only runs after a user click.
function startListening() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    $("voiceTranscript").textContent = "Speech recognition is not supported in this browser. Try Chrome.";
    return;
  }
  if (state.recognition) state.recognition.stop();
  const recognition = new Recognition();
  state.recognition = recognition;
  recognition.lang = "en-IN";
  recognition.interimResults = true;
  recognition.continuous = false;
  $("voiceOrb").classList.add("listening");
  $("voiceTranscript").textContent = "Listening…";
  recognition.onresult = event => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript;
    $("voiceTranscript").textContent = transcript;
    if (event.results[event.results.length - 1].isFinal) {
      $("voiceOrb").classList.remove("listening");
      switchPanel("chat");
      $("chatInput").value = transcript;
      sendChat();
    }
  };
  recognition.onerror = event => {
    $("voiceTranscript").textContent = `Microphone error: ${event.error}. Check browser microphone permission.`;
    $("voiceOrb").classList.remove("listening");
  };
  recognition.onend = () => $("voiceOrb").classList.remove("listening");
  recognition.start();
}
$("listenBtn").addEventListener("click", startListening);
$("stopVoice").addEventListener("click", () => {
  if (state.recognition) state.recognition.stop();
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  $("voiceOrb").classList.remove("listening");
  $("voiceTranscript").textContent = "Voice stopped.";
});

// Local quiz mini-game.
const quizQuestions = [
  {q:"Which language is widely used for AI and automation?",a:["Python","HTML","CSS","SQL only"],correct:0,why:"Python has a large ecosystem for AI, data science and automation."},
  {q:"What does CPU stand for?",a:["Central Processing Unit","Computer Power Utility","Core Program User","Central Print Unit"],correct:0,why:"CPU means Central Processing Unit."},
  {q:"Which command lists files in Linux?",a:["ls","pwd","clear","mkdir"],correct:0,why:"The ls command lists directory contents."},
  {q:"Which one is used to style a web page?",a:["CSS","Python","Git","Flask"],correct:0,why:"CSS controls the visual presentation of HTML."},
  {q:"What does RAM mainly provide?",a:["Temporary working memory","Permanent cloud storage","Internet access","Power supply"],correct:0,why:"RAM holds data and programs currently in use."}
];
$("startQuiz").addEventListener("click", () => {
  state.quiz = {index:0, score:0, questions:[...quizQuestions].sort(() => Math.random() - .5)};
  renderQuiz();
});
function renderQuiz() {
  const area = $("quizArea");
  area.innerHTML = "";
  if (!state.quiz) return;
  const q = state.quiz.questions[state.quiz.index];
  if (!q) {
    const result = document.createElement("p");
    result.textContent = `Finished! Your score: ${state.quiz.score}/${state.quiz.questions.length}.`;
    area.appendChild(result);
    return;
  }
  const title = document.createElement("p");
  title.textContent = `Question ${state.quiz.index + 1}/${state.quiz.questions.length}: ${q.q}`;
  area.appendChild(title);
  const options = document.createElement("div");
  options.className = "quiz-options";
  q.a.forEach((answer, index) => {
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.textContent = answer;
    btn.addEventListener("click", () => {
      const correct = index === q.correct;
      if (correct) state.quiz.score++;
      const feedback = document.createElement("p");
      feedback.textContent = `${correct ? "Correct!" : "Not quite."} ${q.why}`;
      options.replaceChildren(feedback);
      const next = document.createElement("button");
      next.className = "btn primary";
      next.textContent = "NEXT";
      next.addEventListener("click", () => { state.quiz.index++; renderQuiz(); });
      options.appendChild(next);
    });
    options.appendChild(btn);
  });
  area.appendChild(options);
}

// AI-generated interactive text adventure.
$("startAdventure").addEventListener("click", async () => {
  state.adventureStarted = true;
  switchPanel("chat");
  await askDemio(`Be the game master for an interactive text adventure set in: ${$("gameWorld").value}. Start with a vivid but concise opening scene and give me exactly three numbered choices. Wait for my choice before continuing. Keep track of the story within this conversation.`, "game");
});

$("stopVoice").addEventListener("click", () => {
  if ("speechSynthesis" in window) speechSynthesis.cancel();
});
checkHealth();
