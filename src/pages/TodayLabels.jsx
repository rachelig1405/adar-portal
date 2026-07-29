import { useState } from "react";


const API_URL = import.meta.env.VITE_API_URL;
const LOCAL_PRINT_URL = import.meta.env.VITE_LOCAL_PRINT_URL || "http://127.0.0.1:5001";
const PRINT_KEY = import.meta.env.VITE_LOCAL_PRINT_KEY || "adar-print-2026";

export default function TodayLabelsPrint({ onClose }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);

  const printLabels = async () => {
    setLoading(true); setMessage(""); setIsError(false);
    try {
      const zplResponse = await fetch(`${API_URL}/api/labels/today`);
      if (!zplResponse.ok) throw new Error(`שגיאה בקבלת המדבקות: ${await zplResponse.text()}`);
      const zpl = await zplResponse.text();
      if (!zpl.trim()) throw new Error("השרת החזיר מדבקות ריקות");

      const printResponse = await fetch(`${LOCAL_PRINT_URL}/api/print`, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-Print-Key": PRINT_KEY},
        body: JSON.stringify({zpl, job_name: "מדבקות הזמנות להיום"}),
      });
      const result = await printResponse.json();
      if (!printResponse.ok) throw new Error(result.detail || "שגיאה בשרת ההדפסה המקומי");
      setMessage(`נשלחו ${result.labels} מדבקות למדפסת ${result.printer}`);
    } catch (error) {
      console.error(error); setIsError(true);
      setMessage(error instanceof TypeError ? "לא ניתן להתחבר לשרת ההדפסה המקומי. ודא ש-run_server.bat פועל." : error.message);
    } finally { setLoading(false); }
  };

  const checkPrintServer = async () => {
    setLoading(true); setMessage(""); setIsError(false);
    try {
      const response = await fetch(`${LOCAL_PRINT_URL}/api/health`);
      if (!response.ok) throw new Error();
      const result = await response.json();
      setMessage(`שרת ההדפסה פעיל. מדפסת: ${result.configured_printer || result.windows_default_printer || "לא הוגדרה"}`);
    } catch { setIsError(true); setMessage("שרת ההדפסה המקומי אינו פועל"); }
    finally { setLoading(false); }
  };

return (
  <div className="modal-backdrop" dir="rtl">
    <div className="form-window label-print-window">
      <div className="form-header">
        <div>
          <div className="frame-kicker">ADAR Portal</div>
          <strong>הדפסת מדבקות</strong>
        </div>

        <button
          type="button"
          onClick={onClose}
          disabled={loading}
        >
          חזרה
        </button>
      </div>

      <div className="label-print-card">
        <h1 className="label-print-title">
          🖨️ הדפסת מדבקות
        </h1>

        <p className="label-print-subtitle">
          הדפסת מדבקות להזמנות של יום העבודה הנוכחי.
        </p>

        <div className="label-info-box">
          <div className="label-info-row">
            <span className="label-info-title">סוג מדבקה</span>
            <span>הזמנות יום עבודה</span>
          </div>

          <div className="label-info-row">
            <span className="label-info-title">תוכן המדבקה</span>
            <span>
              מספר הזמנה, ברקוד, לקוח, כתובת ועיר
            </span>
          </div>
        </div>

        <div className="label-buttons">
          <button
            type="button"
            className="print-button"
            onClick={printLabels}
            disabled={loading}
          >
            {loading ? "מבצע פעולה..." : "🖨️ הדפס"}
          </button>

          <button
            type="button"
            className="check-button"
            onClick={checkPrintServer}
            disabled={loading}
          >
            בדיקת שרת הדפסה
          </button>

          <button
            type="button"
            className="back-button"
            onClick={onClose}
            disabled={loading}
          >
            חזרה
          </button>
        </div>

        {message && (
          <div
            className={
              isError ? "print-error" : "print-success"
            }
          >
            {message}
          </div>
        )}
      </div>
    </div>
  </div>
);
}

