"use strict";

/* DEMIO FRONTEND CONTROLLER */

const $ = id => document.getElementById(id);
const API = "/api/chat";

let currentMode = "operating";
let conversationHistory = [];
let selectedFiles = [];
let imageFiles = [];
let recognition = null;
let listening = false;
let busy = false;
let waterSeconds = 3600;
let memorySequence = [];
let memoryInput = [];
let quizAnswer = null;

function openMode(mode) {
  currentMode = mode;

  document.querySelectorAll(".panel").forEach(p =>
    p.classList.remove("active-panel")
  );

  document.querySelectorAll(".nav").forEach(b =>
    b.classList.remove("active")
  );

  $(mode).classList.add("active-panel");

  const nav = document.querySelector('[data-mode="' + mode + '"]');
  if (nav) nav.classList.add("active");

  $("operatingStatus").textContent = mode.toUpperCase() + " MODE ACTIVE";

  if (mode !== "talk") stopListening();
}

document.querySelectorAll("[data-mode]").forEach(button => {
  button.addEventListener("click", () => openMode(button.dataset.mode));
});

document.querySelectorAll("[data-open]").forEach(button => {
  button.addEventListener("click", () => openMode(button.dataset.open));
});

/* CHAT */

function addBubble(text, type, files=[]) {
  const div = document.createElement("div");
  div.className = "bubble " + type;

  const name = document.createElement("b");
  name.textContent = type === "bot" ? "DEMIO" : "YOU";
  div.appendChild(name);

  const content = document.createElement("div");
  content.textContent = text;
  div.appendChild(content);

  files.forEach(file => {
    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      div.appendChild(img);
    } else {
      const attachment = document.createElement("div");
      attachment.textContent = "📎 " + file.name;
      div.appendChild(attachment);
    }
  });

  $("messages").appendChild(div);
  $("messages").scrollTop = $("messages").scrollHeight;
}

function showTalkText(text) {
  const line = document.createElement("p");
  line.textContent = text;
  $("talkMessages").appendChild(line);
}

async function askDemio(message, files=[], destination="messages") {
  if (busy) return;

  if (!message.trim() && !files.length) return;

  busy = true;

  if (destination === "messages") {
    addBubble(message || "Please review my uploaded files.", "user", files);
    $("typing").hidden = false;
  } else {
    showTalkText("You: " + (message || "Uploaded files"));
  }

  const form = new FormData();
  form.append("message", message || "Please examine the attached file.");
  form.append("language", "English");
  form.append("history", JSON.stringify(conversationHistory.slice(-12)));

  files.forEach(file => form.append("file", file));

  try {
    const response = await fetch(API, {
      method: "POST",
      body: form
    });

    const raw = await response.text();
    let data;

    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error("Invalid server response: " + raw.slice(0, 300));
    }

    if (!response.ok) {
      throw new Error(
        "HTTP " + response.status + ": " +
        (data.error || data.detail || data.message || raw)
      );
    }

    if (!data.reply) {
      throw new Error("The backend did not return a reply.");
    }

    conversationHistory.push(
      {role: "user", content: message},
      {role: "assistant", content: data.reply}
    );

    if (conversationHistory.length > 20) {
      conversationHistory = conversationHistory.slice(-20);
    }

    if (destination === "messages") {
      addBubble(data.reply, "bot");
    } else if (destination === "talk") {
      showTalkText("DEMIO: " + data.reply);
      speak(data.reply);
    } else {
      $(destination).textContent = data.reply;
    }

    $("operatingStatus").textContent = "RESPONSE RECEIVED";

  } catch (error) {
    console.error(error);

    const errorText = error.message;

    if (destination === "messages") {
      addBubble("Connection error: " + errorText, "bot");
    } else if (destination === "talk") {
      showTalkText("DEMIO connection error: " + errorText);
    } else {
      $(destination).textContent = "Error: " + errorText;
    }

  } finally {
    busy = false;
    $("typing").hidden = true;
  }
}

$("sendButton").addEventListener("click", () => sendChat());

$("messageInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendChat();
});

async function sendChat() {
  const message = $("messageInput").value.trim();
  const files = [...selectedFiles];

  if (!message && !files.length) return;

  $("messageInput").value = "";
  selectedFiles = [];
  renderFileList();

  await askDemio(message, files);
}

$("newChat").addEventListener("click", newConversation);
$("clearChat").addEventListener("click", newConversation);

function newConversation() {
  conversationHistory = [];
  $("messages").innerHTML = "";
  $("talkMessages").innerHTML = "";
  selectedFiles = [];
  renderFileList();
  speechSynthesis.cancel();

  addBubble(
    "A fresh conversation is ready. What would you like to discuss?",
    "bot"
  );
}

/* FILE UPLOAD */

$("fileInput").addEventListener("change", e => {
  selectedFiles.push(...Array.from(e.target.files || []));
  renderFileList();
  e.target.value = "";
});

function renderFileList() {
  $("fileList").innerHTML = "";

  selectedFiles.forEach((file, index) => {
    const tag = document.createElement("span");
    tag.textContent = file.name + " ×";
    tag.style.marginRight = "12px";
    tag.style.cursor = "pointer";

    tag.onclick = () => {
      selectedFiles.splice(index, 1);
      renderFileList();
    };

    $("fileList").appendChild(tag);
  });
}

/* IMAGE MODE */

$("imageInput").addEventListener("change", e => {
  imageFiles = Array.from(e.target.files || []);

  $("imagePreviews").innerHTML = "";

  imageFiles.forEach(file => {
    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      $("imagePreviews").appendChild(img);
    }
  });
});

$("analyzeImages").addEventListener("click", async () => {
  if (!imageFiles.length) {
    $("imageResult").textContent = "Please choose an image or document first.";
    return;
  }

  const question = $("imageQuestion").value.trim() ||
    "Please describe and analyze these uploaded files.";

  await askDemio(question, imageFiles, "imageResult");
});

/* VOICE INPUT */

function createRecognition() {
  const Speech = window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  if (!Speech) {
    alert("Voice recognition requires a supported browser such as Chrome.");
    return null;
  }

  const r = new Speech();
  r.lang = "en-US";
  r.continuous = false;
  r.interimResults = true;

  r.onstart = () => {
    listening = true;
    $("talkMic").classList.add("active");
    $("talkStatus").textContent = "Listening. Speak now...";
    $("operatingStatus").textContent = "LISTENING";
    document.querySelector(".hero")?.classList.add("speaking");
  };

  r.onresult = e => {
    let transcript = "";

    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }

    if (currentMode === "talk") {
      $("talkStatus").textContent = transcript;
      r.finalTranscript = transcript;
    } else {
      $("messageInput").value = transcript;
    }
  };

  r.onerror = e => {
    $("talkStatus").textContent = "Microphone error: " + e.error;
  };

  r.onend = () => {
    listening = false;
    $("talkMic").classList.remove("active");
    document.querySelector(".hero")?.classList.remove("speaking");

    const transcript = r.finalTranscript || "";

    if (currentMode === "talk" && transcript.trim()) {
      askDemio(transcript, [], "talk");
    }

    $("talkStatus").textContent = "Tap the microphone to speak again.";
  };

  return r;
}

function startListening() {
  if (listening) return;

  recognition = createRecognition();
  if (!recognition) return;

  try {
    recognition.start();
  } catch (error) {
    console.error(error);
  }
}

function stopListening() {
  if (recognition && listening) {
    recognition.stop();
  }
}

$("talkMic").addEventListener("click", () => {
  if (listening) stopListening();
  else startListening();
});

$("voiceInput").addEventListener("click", startListening);

/* VOICE OUTPUT */

function speak(text) {
  if (!("speechSynthesis" in window)) return;

  speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 0.95;
  utterance.pitch = 0.85;

  utterance.onstart = () => {
    $("talkStatus").textContent = "DEMIO is speaking...";
    document.querySelector(".hero")?.classList.add("speaking");
  };

  utterance.onend = () => {
    $("talkStatus").textContent = "Tap the microphone to speak again.";
    document.querySelector(".hero")?.classList.remove("speaking");
  };

  speechSynthesis.speak(utterance);
}

/* MENTORING */

document.querySelectorAll("[data-prompt]").forEach(button => {
  button.addEventListener("click", async () => {
    openMode("mentor");
    await askDemio(button.dataset.prompt, [], "mentorResult");
  });
});

$("mentorSend").addEventListener("click", sendMentor);

$("mentorInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendMentor();
});

function sendMentor() {
  const message = $("mentorInput").value.trim();
  if (!message) return;

  $("mentorInput").value = "";
  return askDemio(message, [], "mentorResult");
}

/* GAMES AND EXERCISES */

$("memoryStart").addEventListener("click", () => {
  memorySequence = Array.from({length:5}, () =>
    Math.floor(Math.random() * 9) + 1
  );

  $("memoryArea").textContent =
    "Remember these numbers: " + memorySequence.join("  ");

  setTimeout(() => {
    $("memoryArea").innerHTML = "";

    const input = document.createElement("input");
    input.placeholder = "Type the numbers separated by spaces";
    input.id = "memoryAnswer";

    const check = document.createElement("button");
    check.className = "primary";
    check.textContent = "CHECK";

    check.onclick = () => {
      const answer = $("memoryAnswer").value
        .trim().split(/\s+/).join("");

      const correct = memorySequence.join("");

      $("memoryArea").textContent = answer === correct
        ? "Excellent! You remembered all the numbers! 🎉"
        : "Good try! The correct sequence was " + correct + ". Try again!";

    };

    $("memoryArea").append(input, check);
  }, 4000);
});

const questions = [
  {q:"Which planet is known as the Red Planet?",a:["Earth","Mars","Venus"],correct:1},
  {q:"How many sides does a hexagon have?",a:["Five","Six","Eight"],correct:1},
  {q:"What is 12 × 8?",a:["84","96","108"],correct:1},
  {q:"Which gas do plants absorb?",a:["Oxygen","Carbon dioxide","Hydrogen"],correct:1}
];

$("quizStart").addEventListener("click", () => {
  const q = questions[Math.floor(Math.random()*questions.length)];
  $("quizArea").innerHTML = "";

  const title = document.createElement("p");
  title.textContent = q.q;
  $("quizArea").appendChild(title);

  q.a.forEach((answer,index) => {
    const button = document.createElement("button");
    button.className = "outline";
    button.textContent = answer;
    button.style.margin = "4px";

    button.onclick = () => {
      $("quizArea").textContent = index === q.correct
        ? "Correct! Fantastic work! ⭐"
        : "Not quite. The correct answer is " + q.a[q.correct] + ".";
    };

    $("quizArea").appendChild(button);
  });
});

$("exerciseStart").addEventListener("click", () => {
  const activities = [
    "Stand up and gently stretch your arms.",
    "Take a short walk if it is comfortable.",
    "Relax your shoulders and gently move your neck.",
    "Take a short break away from your screen."
  ];

  $("exerciseArea").textContent =
    activities[Math.floor(Math.random()*activities.length)] +
    " Take it at your own pace.";
});

$("brainStart").addEventListener("click", () => {
  const prompts = [
    "What comes next: 2, 4, 8, 16, __?",
    "If you have 3 boxes with 4 apples each, how many apples are there?",
    "What is the opposite of 'expand'?",
    "Name three things that are blue."
  ];

  $("brainArea").textContent =
    prompts[Math.floor(Math.random()*prompts.length)];
});

/* GENTLE WATER REMINDER — ALL MODES */

const WATER_INTERVAL = 60 * 60;
const WATER_STORAGE = "demio_next_water_time";

let nextWaterTime = Number(localStorage.getItem(WATER_STORAGE));

if (!nextWaterTime || nextWaterTime < Date.now()) {
  nextWaterTime = Date.now() + WATER_INTERVAL * 1000;
  localStorage.setItem(WATER_STORAGE, nextWaterTime);
}

function updateWaterCountdown() {
  let remaining = Math.max(0, Math.ceil(
    (nextWaterTime - Date.now()) / 1000
  ));

  if (remaining <= 0) {
    showWaterReminder();
    nextWaterTime = Date.now() + WATER_INTERVAL * 1000;
    localStorage.setItem(WATER_STORAGE, nextWaterTime);
    remaining = WATER_INTERVAL;
  }

  const mins = Math.floor(remaining / 60);
  const secs = remaining % 60;

  $("waterCountdown").textContent =
    String(mins).padStart(2,"0") + ":" +
    String(secs).padStart(2,"0");
}

function showWaterReminder() {
  $("waterToast").classList.add("show");

  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("DEMIO — A gentle reminder 💧", {
      body: "You've been busy. Would you like a little water? Take care of yourself. ❤️"
    });
  }

  if (currentMode === "talk") {
    $("talkStatus").textContent =
      "A gentle reminder: would you like a little water? 💧";
  }
}

$("closeWater").addEventListener("click", () => {
  $("waterToast").classList.remove("show");
});

$("waterTest").addEventListener("click", showWaterReminder);

setInterval(updateWaterCountdown, 1000);
updateWaterCountdown();

if ("Notification" in window && Notification.permission === "default") {
  document.addEventListener("click", function askNotification() {
    Notification.requestPermission();
    document.removeEventListener("click", askNotification);
  }, {once:true});
}
