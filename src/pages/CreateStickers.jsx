import { useState, useRef } from "react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://adar-portal.onrender.com";

const POLL_INTERVAL_MS = 2500;

export default function CreateProductPdfs() {
  const [excelFile, setExcelFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const pollTimeoutRef = useRef(null);

  const stopPolling = () => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  const pollJobStatus = (jobId) => {
    const poll = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/products/create-pdfs/status/${jobId}`
        );

        if (!response.ok) {
          throw new Error("שגיאה בבדיקת סטטוס התהליך.");
        }

        const data = await response.json();

        if (data.total > 0) {
          setProgress({ current: data.progress, total: data.total });
          setMessage(
            `מייצר קבצים... ${data.progress} מתוך ${data.total} מוצרים`
          );
        }

        if (data.status === "done") {
          setMessage("התהליך הסתיים, מוריד את הקובץ...");
          await downloadZip(jobId);
          setLoading(false);
          return;
        }

        if (data.status === "failed") {
          setError(data.error || "אירעה שגיאה ביצירת הקבצים.");
          setMessage("");
          setLoading(false);
          return;
        }

        pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (pollError) {
        console.error(pollError);
        setError(pollError.message || "אירעה שגיאה בבדיקת סטטוס התהליך.");
        setMessage("");
        setLoading(false);
      }
    };

    poll();
  };

  const downloadZip = async (jobId) => {
    const response = await fetch(
      `${API_URL}/api/products/create-pdfs/download/${jobId}`
    );

    if (!response.ok) {
      throw new Error("הקובץ עדיין לא מוכן להורדה.");
    }

    const blob = await response.blob();

    const contentDisposition = response.headers.get("Content-Disposition");
    let fileName = "product_pdfs.zip";

    const match = contentDisposition?.match(/filename="?([^"]+)"?/);
    if (match?.[1]) {
      fileName = match[1];
    }

    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = fileName;

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(downloadUrl);

    setMessage("התהליך הסתיים וקובץ ה-ZIP הורד.");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setMessage("");
    setError("");
    setProgress({ current: 0, total: 0 });

    if (!excelFile) {
      setError("צריך לבחור קובץ Excel.");
      return;
    }

    const formData = new FormData();
    formData.append("excel_file", excelFile);

    try {
      setLoading(true);
      setMessage("מעלה קובץ Excel...");

      const response = await fetch(
        `${API_URL}/api/products/create-pdfs`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        let errorMessage = "אירעה שגיאה ביצירת הקבצים.";

        try {
          const data = await response.json();
          errorMessage = data.detail || errorMessage;
        } catch {
          // התגובה אינה JSON
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();

      setMessage("הקובץ הועלה, מתחילים ביצירת ה-PDF-ים...");
      pollJobStatus(data.job_id);
    } catch (requestError) {
      console.error(requestError);
      setError(
        requestError.message ||
          "אירעה שגיאה ביצירת תיקי המוצרים."
      );
      setMessage("");
      setLoading(false);
    }
  };

  const progressPercent =
    progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 5;

  return (
    <div
      style={{
        maxWidth: "750px",
        margin: "30px auto",
        padding: "25px",
        background: "#ffffff",
        borderRadius: "14px",
        boxShadow: "0 4px 18px rgba(0,0,0,0.08)",
        direction: "rtl",
      }}
    >
      <h2 style={{ marginTop: 0 }}>
        יצירת תיקי מוצר וקובצי PDF
      </h2>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "22px" }}>
          <label
            style={{
              display: "block",
              fontWeight: "bold",
              marginBottom: "8px",
            }}
          >
            קובץ Excel
          </label>

          <input
            type="file"
            accept=".xlsx,.xls"
            disabled={loading}
            onChange={(event) =>
              setExcelFile(event.target.files?.[0] || null)
            }
          />

          {excelFile && (
            <div style={{ marginTop: "8px" }}>
              נבחר: {excelFile.name}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "13px",
            border: "none",
            borderRadius: "8px",
            background: loading ? "#999999" : "#6f35d2",
            color: "#ffffff",
            fontSize: "17px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading
            ? "יוצר תיקי מוצר..."
            : "התחל יצירת קבצים"}
        </button>
      </form>

      {loading && (
        <div
          style={{
            marginTop: "18px",
            height: "9px",
            background: "#eeeeee",
            borderRadius: "20px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${progressPercent}%`,
              height: "100%",
              background: "#6f35d2",
              borderRadius: "20px",
              transition: "width 0.4s ease",
            }}
          />
        </div>
      )}

      {message && (
        <div
          style={{
            marginTop: "18px",
            padding: "12px",
            background: "#eaf8ed",
            color: "#176b2c",
            borderRadius: "8px",
          }}
        >
          {message}
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: "18px",
            padding: "12px",
            background: "#fff0f0",
            color: "#b00020",
            borderRadius: "8px",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}