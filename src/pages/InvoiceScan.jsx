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
  const [draftLoaded, setDraftLoaded] = useState(false);

  const [keepLocation, setKeepLocation] = useState(true);

  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraTarget, setCameraTarget] = useState(null);

  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const scanLockedRef = useRef(false);
  const nativeScanTimerRef = useRef(null);
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
        throw new Error(
          `Draft load failed: ${response.status}`
        );
      }

      const data = await response.json();

      if (
        Array.isArray(data.rows) &&
        data.rows.length > 0
      ) {
        setRows(data.rows);
      } else {
        const saved =
          localStorage.getItem(STORAGE_KEY);

        if (saved) {
          const parsed =
            JSON.parse(saved);

          if (Array.isArray(parsed)) {
            setRows(parsed);
          }
        }
      }
    } catch (err) {
      console.error(
        "Could not load server draft:",
        err
      );

      try {
        const saved =
          localStorage.getItem(STORAGE_KEY);

        if (saved) {
          const parsed =
            JSON.parse(saved);

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
    } finally {
      setDraftLoaded(true);
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
  if (
    !user?.id ||
    !draftLoaded ||
    rows.length === 0
  ) {
    return;
  }

  const timer = setTimeout(
    async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/inventory-scan/draft`,
          {
            method: "PUT",

            headers: {
              "Content-Type": "application/json",
            },

            body: JSON.stringify({
              user_id: user.id,

              rows: rows.map((row) => ({
                product_barcode: row.product_barcode,
                quantity: Number(row.quantity),
                location: row.location,
              })),
            }),
          }
        );

        if (!response.ok) {
          const text = await response.text();
          throw new Error(text);
        }

        console.log("DRAFT SAVED");

      } catch (err) {
        console.error(
          "Could not save draft:",
          err
        );
      }
    },
    1000
  );

  return () => clearTimeout(timer);

}, [
  rows,
  user?.id,
  draftLoaded
]);
  // -----------------------------------------
  // שמירה אוטומטית בדפדפן
  // -----------------------------------------

  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(rows)
      );
    } catch (err) {
      console.error("Could not save scans:", err);
    }
  }, [rows]);

  // -----------------------------------------
  // סגירת מצלמה
  // -----------------------------------------

  function stopCamera() {
    if (nativeScanTimerRef.current) {
  clearInterval(nativeScanTimerRef.current);
  nativeScanTimerRef.current = null;
}
    try {
      controlsRef.current?.stop();
    } catch (err) {
      console.error(err);
    }

    controlsRef.current = null;

    try {
      BrowserCodeReader.releaseAllStreams?.();
    } catch (err) {
      console.error(err);
    }

    if (videoRef.current) {
      const stream = videoRef.current.srcObject;

      if (stream) {
        stream
          .getTracks()
          .forEach((track) => track.stop());
      }

      try {
        videoRef.current.pause();
      } catch {}

      videoRef.current.srcObject = null;
      videoRef.current.removeAttribute("src");

      try {
        videoRef.current.load();
      } catch {}
    }

    scanLockedRef.current = false;
    setCameraOpen(false);
    setCameraTarget(null);
  }

  function isValidEAN13(code) {
  if (!/^\d{13}$/.test(code)) {
    return false;
  }

  const digits = code.split("").map(Number);

  let sum = 0;

  for (let i = 0; i < 12; i++) {
    sum += digits[i] * (i % 2 === 0 ? 1 : 3);
  }

  const checkDigit = (10 - (sum % 10)) % 10;

  return checkDigit === digits[12];
}
  // -----------------------------------------
  // הפעלת מצלמה
  // -----------------------------------------

  useEffect(() => {
  if (!cameraOpen || !cameraTarget) {
    return;
  }

  let cancelled = false;

  scanLockedRef.current = false;


  // =========================================
  // PRODUCT - EAN13
  // =========================================

  async function startProductScanner() {

    // -----------------------------------------
    // אם הדפדפן תומך ב-BarcodeDetector
    // נשתמש בו קודם
    // -----------------------------------------

    if ("BarcodeDetector" in window) {

      const supportedFormats =
        await window.BarcodeDetector.getSupportedFormats();

      console.log(
        "SUPPORTED BARCODE FORMATS:",
        supportedFormats
      );

      if (supportedFormats.includes("ean_13")) {

        const formats = ["ean_13"];

        if (supportedFormats.includes("upc_a")) {
          formats.push("upc_a");
        }

        const detector =
          new window.BarcodeDetector({
            formats,
          });


        // -------------------------------------
        // פתיחת מצלמה
        // -------------------------------------

        const stream =
          await navigator.mediaDevices.getUserMedia({
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
            },

            audio: false,
          });


        if (cancelled) {
          stream
            .getTracks()
            .forEach((track) => track.stop());

          return;
        }


        videoRef.current.srcObject = stream;

        await videoRef.current.play();


        // -------------------------------------
        // Autofocus
        // -------------------------------------

        try {

          const track =
            stream.getVideoTracks()[0];

          const capabilities =
            track.getCapabilities?.();

          console.log(
            "CAMERA CAPABILITIES:",
            capabilities
          );


          if (
            capabilities?.focusMode?.includes?.(
              "continuous"
            )
          ) {

            await track.applyConstraints({
              advanced: [
                {
                  focusMode: "continuous",
                },
              ],
            });

          }

        } catch (focusError) {

          console.log(
            "Continuous focus unavailable:",
            focusError
          );

        }


        // -------------------------------------
        // סריקה חוזרת של הוידאו
        // -------------------------------------

        nativeScanTimerRef.current =
          setInterval(async () => {

            if (
              cancelled ||
              scanLockedRef.current ||
              !videoRef.current ||
              videoRef.current.readyState < 2
            ) {
              return;
            }


            try {

              const detected =
                await detector.detect(
                  videoRef.current
                );


              if (!detected?.length) {
                return;
              }


              for (const barcode of detected) {

                let value =
                  String(
                    barcode.rawValue || ""
                  ).trim();


                console.log(
                  "NATIVE BARCODE:",
                  value,
                  "FORMAT:",
                  barcode.format
                );


                // UPC-A הוא למעשה EAN13
                // עם 0 בתחילת המספר

                if (
                  barcode.format === "upc_a" &&
                  /^\d{12}$/.test(value)
                ) {
                  value = "0" + value;
                }


                // חייבים 13 ספרות
                if (
                  !/^\d{13}$/.test(value)
                ) {
                  continue;
                }


                // בדיקת ספרת ביקורת
                if (
                  !isValidEAN13(value)
                ) {

                  console.log(
                    "INVALID EAN13 CHECK DIGIT:",
                    value
                  );

                  continue;
                }


                // הצלחה
                scanLockedRef.current = true;

                console.log(
                  "EAN13 SUCCESS:",
                  value
                );

                setProductBarcode(value);


                try {
                  navigator.vibrate?.(150);
                } catch {}


                setTimeout(() => {
                  stopCamera();
                }, 150);


                return;
              }

            } catch (detectError) {

              console.log(
                "BarcodeDetector error:",
                detectError
              );

            }

          }, 120);


        return;
      }
    }


    // =========================================
    // FALLBACK ל-ZXING
    // =========================================

    console.log(
      "Native EAN13 unavailable - using ZXing"
    );


    const hints = new Map();

    hints.set(
      DecodeHintType.POSSIBLE_FORMATS,
      [
        BarcodeFormat.EAN_13,
        BarcodeFormat.UPC_A,
      ]
    );

    hints.set(
      DecodeHintType.TRY_HARDER,
      true
    );


    const reader =
      new BrowserMultiFormatReader(hints);


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
            result.getText()?.trim();


          if (!value) {
            return;
          }


          const format =
            result.getBarcodeFormat();


          console.log(
            "ZXING BARCODE:",
            value,
            "FORMAT:",
            format
          );


          if (
            format === BarcodeFormat.UPC_A &&
            /^\d{12}$/.test(value)
          ) {
            value = "0" + value;
          }


          if (
            !isValidEAN13(value)
          ) {
            return;
          }


          scanLockedRef.current = true;

          setProductBarcode(value);


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


    controlsRef.current = controls;
  }



  // =========================================
  // LOCATION
  // =========================================

  async function startLocationScanner() {

    const hints = new Map();

    hints.set(
      DecodeHintType.POSSIBLE_FORMATS,
      [
        BarcodeFormat.CODE_128,
        BarcodeFormat.QR_CODE,
      ]
    );


    const reader =
      new BrowserMultiFormatReader(hints);


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


          const value =
            result.getText()?.trim();


          if (!value) {
            return;
          }


          scanLockedRef.current = true;

          setLocationBarcode(value);


          try {
            navigator.vibrate?.(100);
          } catch {}


          try {
            controls.stop();
          } catch {}


          setTimeout(() => {
            stopCamera();
          }, 100);
        }
      );


    controlsRef.current = controls;
  }



  // =========================================
  // START
  // =========================================

  async function startScanner() {

    try {

      if (cameraTarget === "product") {

        console.log(
          "STARTING PRODUCT EAN13 SCANNER"
        );

        await startProductScanner();

      } else {

        console.log(
          "STARTING LOCATION SCANNER"
        );

        await startLocationScanner();

      }

    } catch (err) {

      console.error(
        "Camera scanner error:",
        err
      );

      setError(
        "לא ניתן לפתוח או להפעיל את סורק הברקוד"
      );

      stopCamera();
    }
  }


  startScanner();


  return () => {

    cancelled = true;


    if (nativeScanTimerRef.current) {

      clearInterval(
        nativeScanTimerRef.current
      );

      nativeScanTimerRef.current = null;
    }


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
        `חשבונית בסריקה ללא ליקוט${new Date()
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

  try {
    const deleteResponse = await fetch(
      `${API_URL}/api/inventory-scan/draft?user_id=${user.id}`,
      {
        method: "DELETE",
      }
    );

    if (!deleteResponse.ok) {
      const text = await deleteResponse.text();

      throw new Error(
        `Delete draft failed ${deleteResponse.status}: ${text}`
      );
    }

    console.log("DRAFT DELETED");

  } catch (err) {
    console.error(
      "Could not delete server draft:",
      err
    );

    setError(
      "הקובץ ירד, אבל הטיוטה לא נמחקה מהשרת"
    );

    return;
  }

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