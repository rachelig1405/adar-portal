import { useEffect, useState } from "react";
import { API_URL } from "../config";

export default function PickingSummary({user}) {
  const [data, setData] = useState({
    picked_today: 0,
    remaining_today: 0,
    total_today: 0,
    user_piciking_line:0,
    user_avg:0,
    all_piciking:0
     
  });

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSummary() {
      try {
        const response = await fetch(
          `${API_URL}/api/dashboard/picking-summary?userId=${user.id}`
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
      ? (data.all_piciking / data.total_today) * 100
      : 0;

  return (
    <div className="picking-summary">
      <div className="picking-summary-item">
        <span>לוקטו היום</span>
        <strong>{data.picked_today}</strong>
        <small>סה"כ שורות ליקוט</small>
      </div>

      <div className="picking-summary-item">
        <span>נשאר ללקט</span>
        <strong>{data.remaining_today}</strong>
        <small>שורות ליקוט לצפי</small>
      </div>
      <div className="picking-summary-item">
        <span>אתה ליקטת היום</span>
        <strong>{data.user_piciking_line}</strong>
        <small>שורות ליקוט</small>
      </div>
        <div className="picking-summary-item">
        <span>ממצוע זמן ליקוט שלך</span>
        <strong>{data.user_avg}</strong>
        <small>לשורת ליקוט </small>
      </div>

      <div className="picking-progress-wrapper">
        <div>
          {data.all_piciking} מתוך {data.total_today}
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