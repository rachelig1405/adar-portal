import { useEffect, useState } from "react";
import { API_URL } from "../config";

export default function PickingSummary() {
  const [data, setData] = useState({
    picked_today: 0,
    remaining_today: 0,
    total_today: 0,
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSummary() {
      try {
        const response = await fetch(
          `${API_URL}/api/dashboard/picking-summary`
        );

        if (!response.ok) {
          throw new Error("שגיאה בטעינת נתוני הליקוט");
        }

        const result = await response.json();

        setData(result);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    loadSummary();
  }, []);

  if (loading) {
    return (
      <div className="picking-summary">
        טוען נתוני ליקוט...
      </div>
    );
  }

  const progress =
    data.total_today > 0
      ? (data.picked_today / data.total_today) * 100
      : 0;

  return (
    <div className="picking-summary">
      <div className="picking-summary-item">
        <span>לוקטו היום</span>
        <strong>{data.picked_today}</strong>
        <small>שורות ליקוט</small>
      </div>

      <div className="picking-summary-item">
        <span>נשאר ללקט</span>
        <strong>{data.remaining_today}</strong>
        <small>שורות ליקוט</small>
      </div>

      <div className="picking-progress-wrapper">
        <div>
          {data.picked_today} מתוך {data.total_today}
        </div>

        <div className="picking-progress-track">
          <div
            className="picking-progress-bar"
            style={{
              width: `${progress}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}