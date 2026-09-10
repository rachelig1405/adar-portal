import { useEffect, useState } from "react";
import { API_URL } from "../config";

export default function TimeClock({ onClose, user }) {
  const [status, setStatus] = useState(null); // "not_clocked_in" | "clocked_in" | "clocked_out"
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadStatus() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/attendance/status?userId=${user.id}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "שגיאה בטעינת סטטוס נוכחות");
      }

      setStatus(data.status);
    } catch (err) {
      setError(err.message || "שגיאה בטעינת סטטוס נוכחות");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleClockIn() {
    const confirmed = window.confirm("האם להחתים כניסה עכשיו?");

    if (!confirmed) {
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/attendance/clock-in`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "שגיאה בהחתמת כניסה");
      }

      setStatus("clocked_in");
    } catch (err) {
      setError(err.message || "שגיאה בהחתמת כניסה");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleClockOut() {
    const confirmed = window.confirm("האם להחתים יציאה עכשיו?");

    if (!confirmed) {
      return;
    }

    setActionLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/attendance/clock-out`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: user.id }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "שגיאה בהחתמת יציאה");
      }

      setStatus("clocked_out");
    } catch (err) {
      setError(err.message || "שגיאה בהחתמת יציאה");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return <div className="time-clock">טוען סטטוס נוכחות...</div>;
  }

  return (
    <div className="time-clock">
      {error && <div className="time-clock-error">{error}</div>}

      {status === "not_clocked_in" && (
        <button
          type="button"
          className="time-clock-btn clock-in"
          onClick={handleClockIn}
          disabled={actionLoading}
        >
          {actionLoading ? "מחתים..." : "כניסה"}
        </button>
      )}

      {status === "clocked_in" && (
        <button
          type="button"
          className="time-clock-btn clock-out"
          onClick={handleClockOut}
          disabled={actionLoading}
        >
          {actionLoading ? "מחתים..." : "יציאה"}
        </button>
      )}

      {status === "clocked_out" && (
        <div className="time-clock-done">✅ סיימת את יום העבודה היום</div>
      )}
    </div>
  );
}