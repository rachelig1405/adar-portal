import { useEffect, useRef, useState } from "react";
import { API_URL } from "../config";

export default function GeneralChat({ onClose, user }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const messagesEndRef = useRef(null);

  async function loadMessages(showLoading = false) {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const response = await fetch(
        `${API_URL}/api/chat/messages?limit=100`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "שגיאה בטעינת ההודעות"
        );
      }

      setMessages(Array.isArray(data) ? data : []);
      setError("");
    } catch (loadError) {
      console.error(loadError);
      setError(
        loadError.message || "לא ניתן לטעון הודעות"
      );
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    loadMessages(true);

    const intervalId = window.setInterval(() => {
      loadMessages(false);
    }, 3000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  async function sendMessage(event) {
    event.preventDefault();

    const cleanText = text.trim();

    if (!cleanText || sending) {
      return;
    }

    setSending(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/chat/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_id: user.id,
            message: cleanText,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "שגיאה בשליחת ההודעה"
        );
      }

      setText("");
      await loadMessages(false);
    } catch (sendError) {
      console.error(sendError);
      setError(
        sendError.message || "לא ניתן לשלוח הודעה"
      );
    } finally {
      setSending(false);
    }
  }

return (
  <div className="chat-side-panel" dir="rtl">
    <div className="chat-side-header">
      <div>
        <div className="frame-kicker">ADAR Portal</div>
        <strong>צ׳אט עובדים</strong>
      </div>

      <button
        type="button"
        className="chat-close-button"
        onClick={onClose}
      >
        ✕
      </button>
    </div>

    <div className="chat-body">
      {loading && (
        <div className="form-message">
          טוען הודעות...
        </div>
      )}

      {error && (
        <div className="form-error">
          {error}
        </div>
      )}

      <div className="chat-messages">
        {!loading && messages.length === 0 && (
          <div className="chat-empty">
            עדיין אין הודעות בצ׳אט
          </div>
        )}

        {messages.map((message) => {
          const isMine =
            message.sender_id === user.id;

          return (
            <div
              key={message.id}
              className={`chat-message-row ${
                isMine ? "mine" : "other"
              }`}
            >
              <div className="chat-message-bubble">
                {!isMine && (
                  <div className="chat-sender">
                    {message.sender_name}
                  </div>
                )}

                <div className="chat-text">
                  {message.message}
                </div>

                <div className="chat-time">
                  {message.created_at
                    ? new Date(
                        message.created_at
                      ).toLocaleString("he-IL", {
                        hour: "2-digit",
                        minute: "2-digit",
                        day: "2-digit",
                        month: "2-digit",
                      })
                    : ""}
                </div>
              </div>
            </div>
          );
        })}

        <div ref={messagesEndRef} />
      </div>

      <form
        className="chat-compose"
        onSubmit={sendMessage}
      >
        <textarea
          value={text}
          placeholder="כתוב הודעה..."
          maxLength={2000}
          disabled={sending}
          onChange={(event) =>
            setText(event.target.value)
          }
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey
            ) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />

        <button
          type="submit"
          disabled={!text.trim() || sending}
        >
          {sending ? "שולח..." : "שליחה"}
        </button>
      </form>
    </div>
  </div>
);
}