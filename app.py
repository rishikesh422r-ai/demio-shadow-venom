import React, { useState, useRef } from "react";

export default function App() {
  const [mode, setMode] = useState("CHAT");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const fileRef = useRef(null);
  const recognitionRef = useRef(null);

  const uploadFiles = (event) => {
    const selected = Array.from(event.target.files || []);

    const newFiles = selected
      .filter(file =>
        file.type.startsWith("image/") ||
        file.type.startsWith("video/")
      )
      .map(file => ({
        name: file.name,
        type: file.type,
        url: URL.createObjectURL(file)
      }));

    setFiles(previous => [...previous, ...newFiles]);
    event.target.value = "";
  };

  const removeFile = (index) => {
    setFiles(previous => {
      URL.revokeObjectURL(previous[index].url);
      return previous.filter((_, i) => i !== index);
    });
  };

  const sendMessage = () => {
    if (!message.trim() && files.length === 0) return;

    setMessages(previous => [
      ...previous,
      {
        text: message,
        files: [...files]
      }
    ]);

    setMessage("");
    setFiles([]);
  };

  const startVoice = () => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice recognition is not supported in this browser.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      setMessage(event.results[0][0].transcript);
    };

    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const speak = (text) => {
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = "en-IN";

    speech.onstart = () => setSpeaking(true);
    speech.onend = () => setSpeaking(false);

    window.speechSynthesis.speak(speech);
  };

  return (
    <div className="demio">

      <style>{`
        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          background: #03080d;
          color: #d9faff;
          font-family: Arial, sans-serif;
        }

        .demio {
          min-height: 100vh;
          background:
            radial-gradient(circle at center, #062d46 0%, #06121d 45%, #020609 100%);
          padding: 20px;
          overflow-x: hidden;
        }

        .header {
          text-align: center;
          padding: 15px;
          border-bottom: 1px solid #075a76;
          letter-spacing: 7px;
          color: #00eaff;
          text-shadow: 0 0 15px #00dfff;
        }

        .header h1 {
          margin: 0;
          font-size: 32px;
        }

        .header p {
          letter-spacing: 4px;
          font-size: 10px;
          color: #6adfff;
        }

        .status {
          display: flex;
          justify-content: space-between;
          color: #00eaff;
          font-size: 10px;
          margin: 20px 5px;
        }

        .core-area {
          height: 310px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .core {
          width: 220px;
          height: 220px;
          border-radius: 50%;
          border: 2px solid #00dfff;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          box-shadow:
            0 0 15px #00bfff,
            inset 0 0 35px #006b99;
          animation: rotate 12s linear infinite;
        }

        .core::before {
          content: "";
          position: absolute;
          inset: 12px;
          border: 2px dashed #00eaff;
          border-radius: 50%;
        }

        .core::after {
          content: "";
          position: absolute;
          inset: 30px;
          border: 2px solid #007cae;
          border-radius: 50%;
          animation: rotate 5s linear infinite reverse;
        }

        .core-inner {
          width: 95px;
          height: 95px;
          background: radial-gradient(circle, #a3ffff, #00bfff, #003d65);
          border-radius: 50%;
          box-shadow: 0 0 40px #00dfff;
        }

        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .mode-buttons {
          display: flex;
          gap: 10px;
          margin: 15px 0;
        }

        button {
          cursor: pointer;
          color: #00eaff;
          background: #071b29;
          border: 1px solid #008db8;
          padding: 12px;
          border-radius: 6px;
          transition: .2s;
        }

        button:hover {
          background: #06405b;
          box-shadow: 0 0 12px #00cfff;
        }

        .mode-buttons button {
          flex: 1;
        }

        .active {
          background: #07506c;
          box-shadow: 0 0 15px #00bfff;
        }

        .chat-panel {
          height: 220px;
          overflow-y: auto;
          border: 1px solid #087ba2;
          background: rgba(0, 15, 28, .8);
          padding: 12px;
          border-radius: 8px;
        }

        .chat-message {
          background: #06334b;
          padding: 12px;
          margin: 8px 0;
          border-radius: 8px;
          font-size: 13px;
          overflow-wrap: anywhere;
        }

        .upload-area {
          border: 1px dashed #00bfe8;
          padding: 18px;
          text-align: center;
          margin-top: 15px;
          border-radius: 8px;
          color: #71eaff;
        }

        .upload-buttons {
          display: flex;
          justify-content: center;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 12px;
        }

        .preview-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
          gap: 10px;
          margin-top: 15px;
        }

        .preview {
          position: relative;
          background: #071a29;
          padding: 5px;
          border: 1px solid #087ba2;
          border-radius: 8px;
          min-width: 0;
        }

        .preview img,
        .preview video {
          width: 100%;
          height: 100px;
          object-fit: cover;
          border-radius: 5px;
        }

        .preview small {
          display: block;
          overflow-wrap: anywhere;
          font-size: 10px;
          margin-top: 5px;
        }

        .remove {
          position: absolute;
          right: 7px;
          top: 7px;
          background: #8a1425;
          color: white;
          padding: 4px 7px;
        }

        .command {
          display: flex;
          gap: 8px;
          margin-top: 15px;
        }

        .command input {
          min-width: 0;
          flex: 1;
          padding: 14px;
          background: #061522;
          color: white;
          border: 1px solid #008cb9;
          border-radius: 6px;
          outline: none;
        }

        .footer {
          text-align: center;
          color: #267e9b;
          font-size: 10px;
          margin-top: 25px;
          letter-spacing: 3px;
        }

        @media(max-width: 500px) {
          .demio { padding: 10px; }
          .header h1 { font-size: 25px; }
          .core { width: 190px; height: 190px; }
          .core-area { height: 270px; }
        }
      `}</style>

      <div className="header">
        <h1>◈ DEMIO ◈</h1>
        <p>SHADOW VENOM / NEURAL CORE</p>
      </div>

      <div className="status">
        <span>● LINK SECURE</span>
        <span>● SYSTEM ONLINE</span>
      </div>

      <div className="core-area">
        <div className="core">
          <div className="core-inner"></div>
        </div>
      </div>

      <div style={{textAlign:"center", color:"#00dfff"}}>
        {speaking ? "AI SPEAKING..." :
         listening ? "LISTENING..." :
         "NEURAL CORE READY"}
      </div>

      <div className="mode-buttons">
        <button
          className={mode === "VOICE" ? "active" : ""}
          onClick={() => setMode("VOICE")}
        >
          🎙 VOICE
        </button>

        <button
          className={mode === "CHAT" ? "active" : ""}
          onClick={() => setMode("CHAT")}
        >
          ▤ CHAT
        </button>
      </div>

      <div className="chat-panel">
        <div style={{color:"#00eaff", fontSize:"12px"}}>
          ◈ DEMIO SYSTEM
        </div>

        <div className="chat-message">
          Welcome to DEMIO. System initialized.
          {mode === "VOICE"
            ? " Voice mode selected."
            : " Chat mode selected."}
        </div>

        {messages.map((item, index) => (
          <div className="chat-message" key={index}>
            <b>YOU:</b> {item.text}
            {item.files.map((file, i) => (
              <div key={i}>
                {file.name}
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="upload-area">
        <div>◈ MEDIA UPLOAD CENTER ◈</div>

        <div className="upload-buttons">
          <button onClick={() => {
            fileRef.current.accept = "image/*";
            fileRef.current.click();
          }}>
            📷 PHOTOS
          </button>

          <button onClick={() => {
            fileRef.current.accept = "video/*";
            fileRef.current.click();
          }}>
            🎬 VIDEOS
          </button>

          <button onClick={() => {
            fileRef.current.accept = "image/*,video/*";
            fileRef.current.click();
          }}>
            ＋ MEDIA
          </button>
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="image/*,video/*"
          multiple
          hidden
          onChange={uploadFiles}
        />

        <div className="preview-grid">
          {files.map((file, index) => (
            <div className="preview" key={index}>
              <button
                className="remove"
                onClick={() => removeFile(index)}
              >
                ×
              </button>

              {file.type.startsWith("image/") ? (
                <img src={file.url} alt={file.name} />
              ) : (
                <video src={file.url} controls />
              )}

              <small>{file.name}</small>
            </div>
          ))}
        </div>
      </div>

      <div className="command">
        <button onClick={startVoice}>
          {listening ? "⏹" : "🎤"}
        </button>

        <input
          value={message}
          onChange={e => setMessage(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter") sendMessage();
          }}
          placeholder="Enter command..."
        />

        <button onClick={sendMessage}>
          ➤
        </button>
      </div>

      {mode === "VOICE" && (
        <button
          style={{width:"100%", marginTop:10}}
          onClick={() => speak("Welcome to Demio. How can I help you?")}
        >
          🔊 TEST VOICE
        </button>
      )}

      <div className="footer">
        DEMIO AI • NEURAL SYSTEM • 2026
      </div>

    </div>
  );
}
