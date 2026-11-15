import { useEffect, useRef, useState } from "react";
import {
  BrowserCodeReader,
  BrowserMultiFormatReader,
  
} from "@zxing/browser";

import {
  BarcodeFormat,
  DecodeHintType,
} from "@zxing/library";
import { API_URL } from "../config";

const STORAGE_KEY = "adar_inventory_scan_rows_v1";

export default function InvoiceScan({ onClose ,  user}) {
  const [rows, setRows] = useState([]);

  const [productBarcode, setProductBarcode] = useState("");
  const [locationBarcode, setLocationBarcode] = useState("");
  const [quantity, setQuantity] = useState("1");

  const [keepLocation, setKeepLocation] = useState(true);

  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraTarget, setCameraTarget] = useState(null);

  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const scanLockedRef = useRef(false);

  // -----------------------------------------
  // טעינת סריקות שנשמרו בדפדפן
  // -----------------------------------------

 useEffect(() => {
  async function loadDraft() {
    try {
      const response = await fetch(
        `${API_URL}/api/inventory-scan/draft?user_id=${user.id}`
      );

      if (!response.ok) {
        throw new Error("Server draft failed");
      }

      const data = await response.json();

      if (Array.isArray(data.rows) && data.rows.length > 0) {
        // הטיוטה מהשרת קובעת
        setRows(data.rows);
        return;
      }

      // אין טיוטה בשרת - מנסים גיבוי מקומי
      const saved = localStorage.getItem(STORAGE_KEY);

      if (saved) {
        const parsed = JSON.parse(saved);

        if (Array.isArray(parsed)) {
          setRows(parsed);
        }
      }

    } catch (err) {
      console.error("Could not load server draft:", err);

      // השרת לא זמין - ננסה localStorage
      try {
        const saved = localStorage.getItem(STORAGE_KEY);

        if (saved) {
          const parsed = JSON.parse(saved);

          if (Array.isArray(parsed)) {
            setRows(parsed);
          }
        }
      } catch (localErr) {
        console.error(
          "Could not load local draft:",
          localErr
        );
      }
    }
  }

  if (user?.id) {
    loadDraft();
  }
}, [user?.id]);
  /*useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);

      if (saved) {
        const parsed = JSON.parse(saved);

        if (Array.isArray(parsed)) {
          setRows(parsed);
        }
      }
    } catch (err) {
      console.error("Could not load saved scans:", err);
    }
  }, []);
*/
//שמירה אוטומטית בשרת
useEffect(() => {
  if (!user?.id) {
    return;
  }

  const timer = setTimeout(
    async () => {
      try {
        await fetch(
          `${API_URL}/api/inventory-scan/draft`,
          {
            method: "PUT",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              user_id: user.id,
              rows: rows.map((row) => ({
                product_barcode:
                  row.product_barcode,

                quantity:
                  Number(row.quantity),

                location:
                  row.location,
              })),
            }),
          }
        );
      } catch (err) {
        console.error(
          "Could not save draft:",
          err
        );
      }
    },
    1000
  );

  return () => {
    clearTimeout(timer);
  };
}, [rows, user?.id]);
  // -----------------------------------------
  // שמירה אוטומטית בדפדפן
  // -----------------------------------------

  useEffect(() => {
  if (!cameraOpen || !cameraTarget) {
    return;
  }

  let cancelled = false;

  let reader;

  if (cameraTarget === "product") {
    const hints = new Map();

    hints.set(
      DecodeHintType.POSSIBLE_FORMATS,
      [
        BarcodeFormat.EAN_13,

        // חשוב:
        // חלק מברקודי EAN13 שמתחילים ב-0
        // יכולים להיות מזוהים כ-UPC-A
        BarcodeFormat.UPC_A,
      ]
    );

    hints.set(
      DecodeHintType.TRY_HARDER,
      true
    );

    reader =
      new BrowserMultiFormatOneDReader(
        hints
      );

  } else {
    const hints = new Map();

    hints.set(
      DecodeHintType.POSSIBLE_FORMATS,
      [
        BarcodeFormat.CODE_128,
        BarcodeFormat.QR_CODE,
      ]
    );

    reader =
      new BrowserMultiFormatReader(
        hints
      );
  }

  async function startScanner() {
    try {
      scanLockedRef.current = false;

      const controls =
        await reader.decodeFromConstraints(
          {
            video: {
              facingMode: {
                ideal: "environment",
              },

              width: {
                ideal: 1920,
              },

              height: {
                ideal: 1080,
              },

              frameRate: {
                ideal: 30,
                max: 60,
              },
            },

            audio: false,
          },

          videoRef.current,

          (result, error, controls) => {
            if (
              cancelled ||
              !result ||
              scanLockedRef.current
            ) {
              return;
            }

            let value =
              result
                .getText()
                ?.trim();

            if (!value) {
              return;
            }

            const format =
              result.getBarcodeFormat();

            console.log(
              "BARCODE DETECTED:",
              value,
              "FORMAT:",
              BarcodeFormat[format]
            );

            // -------------------------
            // ברקוד מוצר
            // -------------------------

            if (
              cameraTarget === "product"
            ) {
              // לפעמים EAN13 שמתחיל ב-0
              // מוחזר כ-UPC-A של 12 ספרות

              if (
                format ===
                  BarcodeFormat.UPC_A &&
                /^\d{12}$/.test(value)
              ) {
                value = "0" + value;
              }

              if (
                format !==
                  BarcodeFormat.EAN_13 &&
                format !==
                  BarcodeFormat.UPC_A
              ) {
                return;
              }

              if (
                !isValidEAN13(value)
              ) {
                console.log(
                  "INVALID EAN13:",
                  value
                );

                return;
              }
            }

            scanLockedRef.current = true;

            if (
              cameraTarget === "product"
            ) {
              setProductBarcode(value);
            }

            if (
              cameraTarget === "location"
            ) {
              setLocationBarcode(value);
            }

            try {
              navigator.vibrate?.(150);
            } catch {}

            try {
              controls.stop();
            } catch {}

            setTimeout(() => {
              stopCamera();
            }, 150);
          }
        );

      controlsRef.current =
        controls;

      // -------------------------
      // Autofocus
      // -------------------------

      try {
        const stream =
          videoRef.current
            ?.srcObject;

        const track =
          stream
            ?.getVideoTracks?.()[0];

        if (
          track &&
          track.getCapabilities
        ) {
          const capabilities =
            track.getCapabilities();

          console.log(
            "CAMERA CAPABILITIES:",
            capabilities
          );

          if (
            capabilities.focusMode &&
            capabilities.focusMode.includes(
              "continuous"
            )
          ) {
            await track.applyConstraints({
              advanced: [
                {
                  focusMode:
                    "continuous",
                },
              ],
            });

            console.log(
              "CONTINUOUS FOCUS ENABLED"
            );
          }
        }
      } catch (focusError) {
        console.log(
          "FOCUS NOT AVAILABLE:",
          focusError
        );
      }

    } catch (err) {
      console.error(
        "Camera error:",
        err
      );

      setError(
        "לא ניתן לפתוח את המצלמה"
      );

      stopCamera();
    }
  }

  startScanner();

  return () => {
    cancelled = true;

    try {
      controlsRef.current?.stop();
    } catch {}
  };

}, [cameraOpen, cameraTarget]);

  function openProductScanner() {
    setError("");
    setCameraTarget("product");
    setCameraOpen(true);
  }

  function openLocationScanner() {
    setError("");
    setCameraTarget("location");
    setCameraOpen(true);
  }

  // -----------------------------------------
  // הוספת שורה
  // -----------------------------------------

  function addRow(event) {
    event?.preventDefault();

    setError("");

    const product = productBarcode.trim();
    const location = locationBarcode.trim();
    const qty = Number(quantity);

    if (!product) {
      setError("חובה להזין ברקוד מוצר");
      return;
    }

    if (!location) {
      setError("חובה להזין מיקום");
      return;
    }

    if (
      !Number.isFinite(qty) ||
      qty <= 0
    ) {
      setError("יש להזין כמות תקינה");
      return;
    }

    setRows((currentRows) => {
      // אם אותו מוצר באותו מיקום כבר קיים
      // נוסיף לכמות במקום ליצור שורה כפולה

      const existingIndex =
        currentRows.findIndex(
          (row) =>
            row.product_barcode === product &&
            row.location === location
        );

      if (existingIndex >= 0) {
        return currentRows.map(
          (row, index) =>
            index === existingIndex
              ? {
                  ...row,
                  quantity:
                    Number(row.quantity) + qty,
                }
              : row
        );
      }

      return [
        ...currentRows,
        {
          id:
            crypto.randomUUID?.() ||
            `${Date.now()}-${Math.random()}`,

          product_barcode: product,
          quantity: qty,
          location: location,
        },
      ];
    });

    setProductBarcode("");
    setQuantity("1");

    if (!keepLocation) {
      setLocationBarcode("");
    }
  }

  // -----------------------------------------
  // מחיקת שורה
  // -----------------------------------------

  function deleteRow(id) {
    setRows((current) =>
      current.filter(
        (row) => row.id !== id
      )
    );
  }

  // -----------------------------------------
  // שינוי כמות
  // -----------------------------------------

  function changeQuantity(id, value) {
    const qty = Number(value);

    if (!Number.isFinite(qty)) {
      return;
    }

    setRows((current) =>
      current.map((row) =>
        row.id === id
          ? {
              ...row,
              quantity: qty,
            }
          : row
      )
    );
  }

  // -----------------------------------------
  // הורדת Excel
  // -----------------------------------------

  async function finishAndDownload() {
    if (!rows.length) {
      setError("אין סריקות להורדה");
      return;
    }

    setExporting(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/inventory-scan/export`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            rows: rows.map((row) => ({
              product_barcode:
                row.product_barcode,

              quantity:
                Number(row.quantity),

              location:
                row.location,
            })),
          }),
        }
      );

      if (!response.ok) {
        let message =
          "שגיאה ביצירת קובץ Excel";

        try {
          const data =
            await response.json();

          if (data?.detail) {
            message = data.detail;
          }
        } catch {}

        throw new Error(message);
      }

      const blob = await response.blob();

      const url =
        window.URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;

      link.download =
        `סריקות_מלאי_${new Date()
          .toISOString()
          .slice(0, 10)}.xlsx`;

      document.body.appendChild(link);

      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      const clearAfterDownload =
        window.confirm(
          "קובץ Excel ירד בהצלחה.\n\nלמחוק את הסריקות ולהתחיל סריקה חדשה?"
        );

      if (clearAfterDownload) {
        setRows([]);
        setProductBarcode("");
        setLocationBarcode("");
        setQuantity("1");

        localStorage.removeItem(
          STORAGE_KEY
        );
      }
    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "שגיאה בהורדת הקובץ"
      );
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="form-window inventory-scan-window">

        <div className="form-header">
          <div>
            <div className="frame-kicker">
              ADAR Portal
            </div>

            <strong>
              סריקת מלאי למיקום
            </strong>
          </div>

          <button
            type="button"
            onClick={() => {
              stopCamera();
              onClose();
            }}
          >
            חזרה
          </button>
        </div>

        {error && (
          <div className="form-error">
            {error}
          </div>
        )}

        <form
          className="inventory-scan-form"
          onSubmit={addRow}
        >

          <div className="inventory-field">
            <label>
              ברקוד מוצר
            </label>

            <div className="inventory-input-row">
              <input
                type="text"
                value={productBarcode}
                placeholder="סרוק או הקלד ברקוד מוצר"
                autoComplete="off"
                onChange={(e) =>
                  setProductBarcode(
                    e.target.value
                  )
                }
              />

              <button
                type="button"
                className="scan-button"
                onClick={
                  openProductScanner
                }
              >
                📷 סריקה
              </button>
            </div>
          </div>

          <div className="inventory-field">
            <label>
              מיקום
            </label>

            <div className="inventory-input-row">
              <input
                type="text"
                value={locationBarcode}
                placeholder="סרוק או הקלד ברקוד מיקום"
                autoComplete="off"
                onChange={(e) =>
                  setLocationBarcode(
                    e.target.value
                  )
                }
              />

              <button
                type="button"
                className="scan-button"
                onClick={
                  openLocationScanner
                }
              >
                📷 סריקה
              </button>
            </div>
          </div>

          <div className="inventory-field">
            <label>
              כמות
            </label>

            <input
              type="number"
              min="0.01"
              step="0.01"
              value={quantity}
              onChange={(e) =>
                setQuantity(
                  e.target.value
                )
              }
            />
          </div>

          <label className="keep-location">
            <input
              type="checkbox"
              checked={keepLocation}
              onChange={(e) =>
                setKeepLocation(
                  e.target.checked
                )
              }
            />

            השאר את המיקום לשורה הבאה
          </label>

          <button
            type="submit"
            className="save-button"
          >
            הוסף לרשימה
          </button>
        </form>

        <div className="inventory-summary">
          סה״כ שורות:{" "}
          <strong>
            {rows.length}
          </strong>
        </div>

        <div className="inventory-table-wrapper">
          <table className="inventory-table">
            <thead>
              <tr>
                <th>#</th>
                <th>ברקוד מוצר</th>
                <th>כמות</th>
                <th>מיקום</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              {rows.map((row, index) => (
                <tr key={row.id}>
                  <td>
                    {index + 1}
                  </td>

                  <td>
                    {row.product_barcode}
                  </td>

                  <td>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={row.quantity}
                      onChange={(e) =>
                        changeQuantity(
                          row.id,
                          e.target.value
                        )
                      }
                    />
                  </td>

                  <td>
                    {row.location}
                  </td>

                  <td>
                    <button
                      type="button"
                      className="inventory-delete"
                      onClick={() =>
                        deleteRow(row.id)
                      }
                    >
                      מחק
                    </button>
                  </td>
                </tr>
              ))}

              {!rows.length && (
                <tr>
                  <td
                    colSpan="5"
                    className="inventory-empty"
                  >
                    עדיין לא נסרקו מוצרים
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <button
          type="button"
          className="inventory-finish"
          disabled={
            !rows.length ||
            exporting
          }
          onClick={
            finishAndDownload
          }
        >
          {exporting
            ? "יוצר Excel..."
            : "סיום והורדת Excel"}
        </button>

        {cameraOpen && (
          <div className="scanner-overlay">
            <div className="scanner-box">

              <div className="scanner-title">
                {cameraTarget ===
                "product"
                  ? "סריקת ברקוד מוצר"
                  : "סריקת ברקוד מיקום"}
              </div>

              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
              />

              <button
                type="button"
                onClick={
                  stopCamera
                }
              >
                ביטול
              </button>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}