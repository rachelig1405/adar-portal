import { useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://adar-portal.onrender.com";

export default function CreateProductPdfs() {
  const [excelFile, setExcelFile] = useState(null);
  const [certificateFiles, setCertificateFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleCertificateFolder = (event) => {
    const files = Array.from(event.target.files || []);

    const pdfFiles = files.filter((file) =>
      file.name.toLowerCase().endsWith(".pdf")
    );

    setCertificateFiles(pdfFiles);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setMessage("");
    setError("");

    if (!excelFile) {
      setError("צריך לבחור קובץ Excel.");
      return;
    }

    if (certificateFiles.length === 0) {
      setError("צריך לבחור תיקיית תעודות שמכילה קובצי PDF.");
      return;
    }

    const formData = new FormData();

    formData.append("excel_file", excelFile);

    certificateFiles.forEach((file) => {
      formData.append("certificate_files", file);

      formData.append(
        "certificate_paths",
        file.webkitRelativePath || file.name
      );
    });

    try {
      setLoading(true);
      setMessage(
        `מעלה קובץ Excel ו-${certificateFiles.length} תעודות...`
      );

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

      const blob = await response.blob();

      const contentDisposition =
        response.headers.get("Content-Disposition");

      let fileName = "product_pdfs.zip";

      const match = contentDisposition?.match(
        /filename="?([^"]+)"?/
      );

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
    } catch (requestError) {
      console.error(requestError);
      setError(
        requestError.message ||
          "אירעה שגיאה ביצירת תיקי המוצרים."
      );
      setMessage("");
    } finally {
      setLoading(false);
    }
  };

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

        <div style={{ marginBottom: "22px" }}>
          <label
            style={{
              display: "block",
              fontWeight: "bold",
              marginBottom: "8px",
            }}
          >
            תיקיית תעודות
          </label>

          <input
            type="file"
            accept=".pdf,application/pdf"
            multiple
            webkitdirectory=""
            directory=""
            disabled={loading}
            onChange={handleCertificateFolder}
          />

          <div
            style={{
              marginTop: "8px",
              color:
                certificateFiles.length > 0
                  ? "#087f23"
                  : "#666666",
            }}
          >
            {certificateFiles.length > 0
              ? `נבחרו ${certificateFiles.length} קובצי PDF`
              : "לא נבחרה תיקייה"}
          </div>
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
              width: "60%",
              height: "100%",
              background: "#6f35d2",
              borderRadius: "20px",
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