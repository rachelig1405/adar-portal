import { createContext, useContext, useEffect, useRef, useState } from "react";
import { API_URL } from "./config";

const ChatContext = createContext(null);

export function ChatProvider({ user, children }) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const knownMessageIdsRef = useRef(new Set());
  const isFirstLoadRef = useRef(true);
  const isChatOpenRef = useRef(false);

  useEffect(() => {
    isChatOpenRef.current = isChatOpen;
  }, [isChatOpen]);

  function playNotificationSound() {
    try {
      const AudioContextClass =
        window.AudioContext || window.webkitAudioContext;
      const audioContext = new AudioContextClass();

      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(880, audioContext.currentTime);

      gainNode.gain.setValueAtTime(0.15, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.001,
        audioContext.currentTime + 0.35
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.35);
    } catch (soundError) {
      console.error("שגיאה בהשמעת צליל התראה:", soundError);
    }
  }

  function showBrowserNotification(message) {
    if (typeof Notification === "undefined") {
      return;
    }

    if (Notification.permission === "granted") {
      const notification = new Notification(
        message.sender_name || "הודעה חדשה בצ׳אט",
        {
          body: message.message,
          icon: "/favicon.ico",
        }
      );

      notification.onclick = () => {
        window.focus();
        setIsChatOpen(true);
      };
    }
  }

  useEffect(() => {
    if (
      typeof Notification !== "undefined" &&
      Notification.permission === "default"
    ) {
      Notification.requestPermission();
    }
  }, []);

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

      const newMessages = Array.isArray(data) ? data : [];

      if (!isFirstLoadRef.current) {
        const incomingNewMessages = newMessages.filter(
          (message) =>
            !knownMessageIdsRef.current.has(message.id) &&
            message.sender_id !== user.id
        );

        if (incomingNewMessages.length > 0) {
          playNotificationSound();

          if (!isChatOpenRef.current) {
            showBrowserNotification(
              incomingNewMessages[incomingNewMessages.length - 1]
            );
            setUnreadCount((current) => current + incomingNewMessages.length);
          }
        }
      }

      knownMessageIdsRef.current = new Set(
        newMessages.map((message) => message.id)
      );
      isFirstLoadRef.current = false;

      setMessages(newMessages);
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

  // *** זה ה-useEffect שהוחלף - הגרסה החדשה עם Visibility API ***
  useEffect(() => {
    let intervalId = null;

    function startPolling() {
      if (intervalId) return;

      loadMessages(false);
      intervalId = window.setInterval(() => {
        loadMessages(false);
      }, 3000);
    }

    function stopPolling() {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    }

    function handleVisibilityChange() {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    }

    loadMessages(true);

    if (!document.hidden) {
      startPolling();
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  async function sendMessage(text) {
    const cleanText = text.trim();

    if (!cleanText) {
      return;
    }

    const response = await fetch(`${API_URL}/api/chat/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user.id,
        message: cleanText,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "שגיאה בשליחת ההודעה"
      );
    }

    await loadMessages(false);
  }

  const value = {
    messages,
    loading,
    error,
    sendMessage,
    isChatOpen,
    unreadCount,
    openChat: () => {
      setIsChatOpen(true);
      setUnreadCount(0);
    },
    closeChat: () => setIsChatOpen(false),
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);

  if (!context) {
    throw new Error("useChat חייב לשמש בתוך ChatProvider");
  }

  return context;
}