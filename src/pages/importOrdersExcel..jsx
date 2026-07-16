import { useState } from "react";
import { API_URL } from "../config";

export default function ImportOrdersExcel({
  onClose,
}) {
  const [file, setFile] = useState(null);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();

    if (!file) {
      setError("חובה לבחור קובץ Excel");
      return;
    }

    setSaving(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API_URL}/api/orders/import-excel`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(
                data.detail || data
              )
        );
      }

      setResult(data);
    } catch (submitError) {
      console.error(submitError);

      setError(
        submitError.message ||
          "שגיאה בקליטת קובץ האקסל"
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="form-window">
        <div className="form-header">
          <div>
            <div className="frame-kicker">
              ADAR Portal
            </div>

            <strong>
              קליטת הזמנות מאקסל
            </strong>
          </div>

          <button
            type="button"
            onClick={onClose}
          >
            חזרה
          </button>
        </div>

        <form
          className="order-form"
          onSubmit={submit}
        >
          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          <label>קובץ Excel</label>

          <input
            type="file"
            accept=".xlsx,.xlsm"
            onChange={(event) => {
              setFile(
                event.target.files?.[0] ||
                  null
              );
              setResult(null);
            }}
          />

          {file && (
            <div className="selected-file">
              <strong>{file.name}</strong>

              <span>
                {Math.ceil(file.size / 1024)}
                {" "}KB
              </span>
            </div>
          )}

          <button
            className="save-button"
            type="submit"
            disabled={saving || !file}
          >
            {saving
              ? "קולט הזמנות..."
              : "קלוט הזמנות מהאקסל"}
          </button>

          {result && (
            <div className="import-result">
              <h3>תוצאות הקליטה</h3>

              <p>
                נקלטו בהצלחה:{" "}
                <strong>
                  {result.created_count}
                </strong>
              </p>

              <p>
                נכשלו:{" "}
                <strong>
                  {result.failed_count}
                </strong>
              </p>

              {result.errors?.length > 0 && (
                <div className="import-errors">
                  {result.errors.map(
                    (item) => (
                      <div
                        key={`${item.excel_row}-${item.order_number}`}
                      >
                        שורה {item.excel_row},
                        הזמנה{" "}
                        {item.order_number ||
                          "ללא מספר"}:
                        {" "}
                        {typeof item.error ===
                        "string"
                          ? item.error
                          : JSON.stringify(
                              item.error
                            )}
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}