import { useState } from "react";

function TodayLabelsPrint({ onClose }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const printLabels = async () => {
    try {
      setLoading(true);
      setMessage("");

      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/labels/today`
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
      }

      const zpl = await response.text();

      window.BrowserPrint.getDefaultDevice(
        "printer",
        (printer) => {
          printer.send(
            zpl,
            () => {
              setMessage("המדבקות נשלחו למדפסת");
              setLoading(false);
            },
            (error) => {
              setMessage(`שגיאת הדפסה: ${error}`);
              setLoading(false);
            }
          );
        },
        (error) => {
          setMessage(`לא נמצאה מדפסת Zebra: ${error}`);
          setLoading(false);
        }
      );
    } catch (error) {
      setMessage(error.message);
      setLoading(false);
    }
  };

  return (
   <div className="label-print-page">

    <div className="label-print-card">

        <h1 className="label-print-title">
            🖨️ הדפסת מדבקות
        </h1>

        <p className="label-print-subtitle">
            הדפסת כל ההזמנות של יום העבודה הנוכחי.
        </p>

        <div className="label-info-box">

            <div className="label-info-row">
                <span className="label-info-title">
                    סוג מדבקה
                </span>

                <span>
                    הזמנות יום עבודה
                </span>
            </div>

            <div className="label-info-row">
                <span className="label-info-title">
                    תוכן המדבקה
                </span>

                <span>
                    מספר הזמנה, ברקוד, לקוח, כתובת ועיר
                </span>
            </div>

        </div>

        <div className="label-buttons">

            <button
                className="print-button"
                onClick={printLabels}
                disabled={loading}
            >
             {loading ? "שולח למדפסת..." : "🖨️ הדפס"}
            </button>

            <button
                className="back-button"
                onClick={onClose}
            >
                חזרה
            </button>

        </div>
        {message && (
            <div
                className={
                    message.includes("שגיאת") ||
                    message.includes("לא נמצאה")
                        ? "print-error"
                        : "print-success"
                }
            >
                {message}
            </div>
        )}

    </div>

</div>
  );
}

export default TodayLabelsPrint;