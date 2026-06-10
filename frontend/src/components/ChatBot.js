import React, { useState, useRef, useEffect } from "react";
import { sendGptbotsMessage, confirmGptbotsEntry } from "../services/api";

const STORAGE_KEY = "chatbot_state";

function loadState() {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return null;
}

function saveState(messages, conversationId) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, conversationId }));
  } catch {}
}

const INITIAL = [
  {
    role: "bot",
    text: "Hello! I'm connected to GPTBots. Tell me what you worked on and I'll log it automatically.",
  },
];

const HINT_TEXT =
  "\n\n(Tip: tell me what you worked on, e.g. 'I worked 4 hours on project 1904 preparing doc DOC-001')";

export default function ChatBot({ onSaved }) {
  const saved = loadState();
  const [messages, setMessages] = useState(saved?.messages ?? INITIAL);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [gptConversationId, setGptConversationId] = useState(saved?.conversationId ?? null);
  const [pendingEntry, setPendingEntry] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    saveState(messages, gptConversationId);
  }, [messages, gptConversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    if (pendingEntry) {
      const lower = text.trim().toLowerCase();
      if (lower === "ok" || lower === "save" || lower === "sure" || lower === "confirm" || lower === "yes" || lower === "y" || lower === "add to entry" || lower === "add to draft" || lower === "add entry" || lower === "save entry") {
        setLoading(true);
        try {
          const saveResult = await confirmGptbotsEntry(pendingEntry, text);
          const saved = saveResult.entry || pendingEntry;
          const isOther = (saved.activity_type || pendingEntry.activity_type) === "other";
          setMessages((prev) => [
            ...prev,
            { role: "user", text },
            {
              role: "bot",
              text: isOther
                ? `✅ Entry saved: ${saved.activity_time || pendingEntry.activity_time}h on ${saved.activity_code || pendingEntry.activity_code || "activity"}`
                : `✅ Entry saved: ${saved.work_time || pendingEntry.work_time}h work (reviewer: ${saved.reviewer_time || pendingEntry.reviewer_time || 0}h) on project ${saved.project_id || pendingEntry.project_id}`,
            },
          ]);
          setPendingEntry(null);
          setGptConversationId(null);
          if (onSaved) onSaved();
        } catch (err) {
          setMessages((prev) => [...prev, { role: "user", text }, { role: "bot", text: `Error: ${err.message}` }]);
        }
        setLoading(false);
        return;
      }
      if (lower === "cancel" || lower === "no" || lower === "n" || lower === "nevermind") {
        setMessages((prev) => [...prev, { role: "user", text }, { role: "bot", text: "Entry cancelled." }]);
        setPendingEntry(null);
        setGptConversationId(null);
        return;
      }
      // User is correcting the draft — send refinement to GPTBots
      setMessages((prev) => [...prev, { role: "user", text }]);
      setLoading(true);
      try {
        const result = await sendGptbotsMessage(text, gptConversationId, pendingEntry);
        setGptConversationId(result.conversation_id);
        if (result.entry_preview) {
          setPendingEntry(result.entry_preview);
          const r = result.reply || "Draft updated.";
          setMessages((prev) => [...prev, { role: "bot", text: r + "\n\nType **ok** to save this entry, or tell me what to change." }]);
        } else {
          setPendingEntry(null);
          setMessages((prev) => [...prev, { role: "bot", text: (result.reply || "Draft updated.") + HINT_TEXT }]);
        }
      } catch (err) {
        setMessages((prev) => [...prev, { role: "bot", text: `Error: ${err.message}` }]);
      }
      setLoading(false);
      return;
    }

    setMessages((prev) => [...prev, { role: "user", text }]);

    setLoading(true);
    try {
      const result = await sendGptbotsMessage(text, gptConversationId);
      setGptConversationId(result.conversation_id);
      let reply = result.reply;

      if (result.entry_preview) {
        setPendingEntry(result.entry_preview);
        reply = result.reply + "\n\nType **ok** to save this entry, or tell me what to change.";
        setMessages((prev) => [...prev, { role: "bot", text: reply }]);
      } else {
        reply = result.reply + HINT_TEXT;
        setMessages((prev) => [...prev, { role: "bot", text: reply }]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: "bot", text: `Error: ${err.message}` }]);
    }
    setLoading(false);
  };

  const handleNewSession = () => {
    setMessages(INITIAL);
    setGptConversationId(null);
    setPendingEntry(null);
    sessionStorage.removeItem(STORAGE_KEY);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <button className="btn btn-sm btn-outline" onClick={handleNewSession}>
          New Session
        </button>
      </div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-message-${msg.role}`}>
            <div className="chat-bubble">{msg.text}</div>
          </div>
        ))}
        {loading && (
          <div className="chat-message chat-message-bot">
            <div className="chat-bubble">Thinking...</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="chat-input-bar">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Enter to send)"
          rows="2"
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
