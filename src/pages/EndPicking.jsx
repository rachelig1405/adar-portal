import { useState } from "react";
import { API_URL } from "../config";

// Place this file alongside EndPicking.jsx, using the same relative API_URL import.
// The server endpoint must enforce the portal's normal authentication and report permissions.
export default function ExportMissingFactoryReport({ onClose }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function downloadReport(event) {
    event.preventDefault();
    if (saving) return;

    setSaving(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/reports/missing-factory-excel`,
        {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        }
      );

      if (!response.ok) {
        let message = "שגיאה בהפקת דוח החוסרים";
        try {
          const data = await response.json();
          if (typeof data.detail === "string") message = data.detail;
        } catch {
          message = `שגיאה בהפקת הדוח (${response.status})`;
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("content-disposition") || "";
      const match = contentDisposition.match(/filename\s*=\s*"?([^";]+)"?/i);
      const filename = match?.[1] || "Missing_Factory_Orders.xlsx";

      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
    } catch (downloadError) {
      console.error(downloadError);
      setError(downloadError.message || "לא ניתן להוריד את הדוח");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" dir="rtl">
      <div className="form-window picking-window">
        <div className="form-header">
          <div>
            <div className="frame-kicker">ADAR Portal</div>
            <strong>דוח חוסרים לפי מפעלים</strong>
          </div>
          <button type="button" onClick={onClose} disabled={saving}>
            חזרה
          </button>
        </div>

        <form className="order-form" onSubmit={downloadReport}>
          <div className="picker-section">
            <label>ייצוא דוח חוסרים</label>
            <div className="form-message">
              הפקת קובץ Excel חדש עם כל הפריטים החסרים, כולל גיליון סיכום
              וגיליון נפרד לכל מפעל.
              <div>הקובץ המקורי ב־Nutstore לא ישתנה.</div>
            </div>
          </div>

          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}

          <button className="save-button" type="submit" disabled={saving}>
            {saving ? "מכין דוח חוסרים..." : "ייצוא דוח חוסרים לאקסל"}
          </button>
        </form>
      </div>
    </div>
  );
}
