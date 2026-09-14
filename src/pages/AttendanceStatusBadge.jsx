import { useEffect, useState } from "react";
import { API_URL } from "../config";

export default function AttendanceStatusBadge({ user }) {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      try {
        const response = await fetch(
          `${API_URL}/api/attendance/status?userId=${user.id}`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "שגיאה בטעינת סטטוס נוכחות");
        }

        if (!cancelled) {
          setStatus(data.status);
        }
      } catch (error) {
        console.error(error);
      }
    }

    loadStatus();

    // רענון אוטומטי כל דקה, כדי שהתג יתעדכן גם בלי רענון ידני של הדף
    const interval = setInterval(loadStatus, 60000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [user.id]);

  if (status === "clocked_in") {
    return (
      <div className="attendance-badge attendance-badge-active">
        <span className="attendance-dot" />
        פעיל
      </div>
    );
  }

  if (status === "clocked_out") {
    return (
      <div className="attendance-badge attendance-badge-inactive">
        <span className="attendance-dot" />
        סיים יום
      </div>
    );
  }

  if (status === "not_clocked_in") {
    return (
      <div className="attendance-badge attendance-badge-inactive">
        <span className="attendance-dot" />
        לא פעיל
      </div>
    );
  }

  return null; // עדיין בטעינה
}