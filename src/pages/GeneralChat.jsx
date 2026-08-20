import { useEffect, useRef } from "react";
import { useChat } from "./ChatContext";

export default function GeneralChat({ onClose, user}) {
  const { messages, loading, error, sendMessage ,openChat,closeChat } = useChat();

  const messagesEndRef = useRef(null);

    useEffect(() => {
    openChat();
    return () => {
      closeChat();
    };
  }, []);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  async function handleSubmit(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const textarea = form.elements.namedItem("chatText");
    const value = textarea.value;

    try {
      await sendMessage(value);
      textarea.value = "";
    } catch (sendError) {
      console.error(sendError);
    }
  }

  return (
    <div className="chat-side-panel" dir="rtl">
      <div className="chat-side-header">
        <div>
          <div className="frame-kicker">ADAR Portal</div>
          <strong>צ׳אט עובדים</strong>
        </div>

        <button type="button" className="chat-close-button" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="chat-body">
        {loading && <div className="form-message">טוען הודעות...</div>}

        {error && <div className="form-error">{error}</div>}

        <div className="chat-messages">
          {!loading && messages.length === 0 && (
            <div className="chat-empty">עדיין אין הודעות בצ׳אט</div>
          )}

          {messages.map((message) => {
            const isMine = message.sender_id === user.id;

            return (
              <div
                key={message.id}
                className={`chat-message-row ${isMine ? "mine" : "other"}`}
              >
                <div className="chat-message-bubble">
                  {!isMine && (
                    <div className="chat-sender">{message.sender_name}</div>
                  )}

                  <div className="chat-text">{message.message}</div>

                  <div className="chat-time">
                    {message.created_at
                      ? new Date(message.created_at).toLocaleString("he-IL", {
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

        <form className="chat-compose" onSubmit={handleSubmit}>
          <textarea
            name="chatText"
            placeholder="כתוב הודעה..."
            maxLength={2000}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />

          <button type="submit">שליחה</button>
        </form>
      </div>
    </div>
  );
}