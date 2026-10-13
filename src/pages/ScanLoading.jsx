import { useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";

import {
  BarcodeFormat,
  DecodeHintType
} from "@zxing/library";

const API_URL = import.meta.env.VITE_API_URL;

export default function ScanLoading({ user, onClose, }) {
  const videoRef = useRef(null);
  const controlsRef = useRef(null);
  const scanInProgressRef = useRef(false);

  const [cameraOpen, setCameraOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const [manualOrder, setManualOrder] = useState("");
  const [lastScan, setLastScan] = useState(null);
  const [message, setMessage] = useState("");
  const [
  finishPreviewOpen,
  setFinishPreviewOpen
 ] = useState(false);

const [
  finishPreviewOrders,
  setFinishPreviewOrders
 ] = useState([]);

const [
  finishPreviewLoading,
  setFinishPreviewLoading
] = useState(false);

  const [summary, setSummary] = useState({
    expected: 0,
    loaded: 0,
    remaining: 0,
  });
  const [torchAvailable, setTorchAvailable] =
  useState(false);

  const [torchOn, setTorchOn] =
  useState(false);
  const [orders, setOrders] = useState([]);
  const [finishing, setFinishing] = useState(false);
  const [loadingFinished, setLoadingFinished] = useState(false);

  useEffect(() => {
    loadSummary();

    return () => {
      stopCamera();
    };
  }, []);

  // =====================================================
  // סיכום ההעמסה
  // =====================================================

  async function loadSummary() {
    try {
      const response = await fetch(
        `${API_URL}/api/loading/summary`
      );

      const data = await response.json();

      if (data.success) {
        setSummary(data.summary);
        setOrders(data.orders || []);
      }
      return data; 
    } catch (error) {
      console.error("Summary error:", error);
    }
  }

  // =====================================================
  // עצירת מצלמה
  // =====================================================

  function stopCamera() {
    try {
      controlsRef.current?.stop();

      if (videoRef.current?.srcObject) {
        const tracks =
          videoRef.current.srcObject.getTracks();

        tracks.forEach((track) =>
          track.stop()
        );

        videoRef.current.srcObject = null;
      }
    } catch (error) {
      console.error(error);
    }

    controlsRef.current = null;
    setCameraOpen(false);
    
  }

  //סיום העמסה
  async function finishLoading() {
  if (finishing) {
    return;
  }

  setFinishing(true);
  setMessage("");

  try {
    // מביאים מצב עדכני ממש עכשיו
    const current = await loadSummary();

    if (!current?.success) {
      setMessage(
        "לא ניתן לקבל את מצב ההעמסה"
      );
      return;
    }

    const currentOrders =
      current.orders || [];

    // כל הזמנה שבה הצפי לא תואם למה שהועמס
    const gaps = currentOrders.filter(
      (order) =>
        Number(order.loaded || 0) !==
        Number(order.expected || 0)
    );

    let notes = null;

    // =========================
    // יש פערים
    // =========================

    if (gaps.length > 0) {
      const gapText = gaps
        .map((order) => {
          const expected =
            Number(order.expected || 0);

          const loaded =
            Number(order.loaded || 0);

          const difference =
            loaded - expected;

          let status = "";

          if (difference < 0) {
            status =
              `חסרים ${Math.abs(difference)} משטחים`;
          } else {
            status =
              `עודף ${difference} משטחים`;
          }

          return (
            `הזמנה ${order.order_number}\n` +
            `צפי: ${expected} | ` +
            `הועמסו: ${loaded}\n` +
            `${status}`
          );
        })
        .join("\n\n");

      const confirmed =
        window.confirm(
          `קיימים פערים בהעמסה:\n\n` +
          `${gapText}\n\n` +
          `האם לסיים את ההעמסה בכל זאת?`
        );

      if (!confirmed) {
        return;
      }

      notes = window.prompt(
        "ניתן להוסיף הערה לסיום ההעמסה:"
      );
    }

    // =========================
    // אין פערים
    // =========================

    if (gaps.length === 0) {
      const confirmed =
        window.confirm(
          "כל המשטחים הועמסו בהתאם לצפי.\n\n" +
          "האם לסיים את ההעמסה?"
        );

      if (!confirmed) {
        return;
      }
    }

    // =========================
    // סגירת ההעמסה בשרת
    // =========================

    const response = await fetch(
      `${API_URL}/api/loading/finish`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          worker_id: user.id,
          notes: notes || null,
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "שגיאה בסיום ההעמסה"
      );
    }

    if (data.success) {
      setLoadingFinished(true);

      setMessage(
        data.message ||
        "העמסה נסגרה בהצלחה"
      );

      setLastScan(null);
    }

  } catch (error) {
    console.error(
      "Finish loading error:",
      error
    );

    setMessage(
      error.message ||
      "לא ניתן לסיים את ההעמסה"
    );

  } finally {
    setFinishing(false);
  }
}
 async function openFinishPreview() {
  if (finishPreviewLoading) {
    return;
  }

  setFinishPreviewLoading(true);

  try {
    const response = await fetch(
      `${API_URL}/api/loading/finish-preview`
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail ||
        "שגיאה בטעינת סיכום ההעמסה"
      );
    }

    setFinishPreviewOrders(
      data.orders || []
    );

    setFinishPreviewOpen(true);

  } catch (error) {
    console.error(error);

    setMessage(
      error.message ||
      "לא ניתן לקבל את סיכום ההעמסה"
    );

  } finally {
    setFinishPreviewLoading(false);
  }
}
  // =====================================================
  // פתיחת מצלמה לסריקה אחת בלבד
  // =====================================================

  async function improveCamera(videoElement) {
  try {
    const stream = videoElement?.srcObject;

    if (!stream) {
      console.log("No camera stream");
      return;
    }

    const track = stream
      .getVideoTracks()[0];

    if (!track) {
      console.log("No video track");
      return;
    }

    const capabilities =
      track.getCapabilities?.() || {};

    console.log(
      "Camera capabilities:",
      capabilities
    );

    const advanced = [];

    // =========================
    // פוקוס רציף
    // =========================

    if (
      capabilities.focusMode &&
      capabilities.focusMode.includes(
        "continuous"
      )
    ) {
      advanced.push({
        focusMode: "continuous",
      });
    }

    // =========================
    // זום
    // =========================

    if (
      capabilities.zoom &&
      typeof capabilities.zoom.min ===
        "number"
    ) {
      const min =
        capabilities.zoom.min;

      const max =
        capabilities.zoom.max;

      // זום מתון כדי לא לפגוע בחדות
      const targetZoom = Math.min(
        Math.max(1.5, min),
        max
      );

      advanced.push({
        zoom: targetZoom,
      });
    }

    if (advanced.length > 0) {
      await track.applyConstraints({
        advanced,
      });
    }

    console.log(
      "Camera enhancements applied"
    );

  } catch (error) {
    console.error(
      "Camera enhancement error:",
      error
    );
  }
}
async function startCamera() {
  if (loading || cameraOpen) {
    return;
  }

  setMessage("");
  setLastScan(null);
  scanInProgressRef.current = false;

  try {
    // קודם מציגים את אזור המצלמה
    setCameraOpen(true);

    // מחכים ש-React באמת יצור את <video>
    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(resolve);
      });
    });

    const videoElement = videoRef.current;

    if (!videoElement) {
      throw new Error(
        "Video element not available"
      );
    }

    const hints = new Map();

    hints.set(
    DecodeHintType.POSSIBLE_FORMATS,
    [
        BarcodeFormat.CODE_128
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
          audio: false,

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
            advanced: [
            {
            focusMode: "continuous",
            },
  ],
        },
        },

        videoElement,

        async (
          result,
          error,
          controlsFromCallback
        ) => {
          if (!result) {
            return;
          }

          if (
            scanInProgressRef.current
          ) {
            return;
          }

          const orderNumber =
            result.getText()?.trim();

          if (!orderNumber) {
            return;
          }

          scanInProgressRef.current = true;

          try {
            controlsFromCallback?.stop();
          } catch {}

          stopCamera();

          await processScan(
            orderNumber
          );
        }
      );

    controlsRef.current = controls;
    await improveCamera(
    videoElement
    );

  } catch (error) {
    console.error(
      "Camera error:",
      error
    );

    stopCamera();

    setMessage(
      "לא ניתן לפתוח את המצלמה"
    );
  }
}

  // =====================================================
  // קריאה ל-API
  // הפונקציה הזאת גם מטפלת באישורי חריגה
  // =====================================================

  async function requestScan(
    orderNumber,
    options = {}
  ) {
    const response = await fetch(
      `${API_URL}/api/loading/scan`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          order_number: orderNumber,

          // חייב להיות Record ID של העובד ב-Airtable
          worker_id: user.id,

          notes: null,

          confirm_overage:
            options.confirm_overage ||
            false,

          confirm_not_in_forecast:
            options.confirm_not_in_forecast ||
            false,
          confirm_not_in_line:
            options.confirm_not_in_line ||
            false,
        }),
      }
    );

    const data = await response.json();

    // ==========================================
    // הזמנה לא בצפי
    // ==========================================

    if (
      data.code ===
      "NOT_IN_FORECAST"
    ) {
      const confirmed =
        window.confirm(
          "משטח זה לא מופיע בצפי האספקה להיום.\n\nהאם לאשר את הסריקה?"
        );

      if (!confirmed) {
        return null;
      }

      return requestScan(
        orderNumber,
        {
          ...options,
          confirm_not_in_forecast:
            true,
        }
      );
    }
    if (
      data.code ===
      "NOT_IN_LINE"
    ) {
      const confirmed =
        window.confirm(
          "משטח זה לא מופיע בקו הפצה סוסנא.\n\nהאם לאשר את הסריקה?"
        );

      if (!confirmed) {
        return null;
      }

      return requestScan(
        orderNumber,
        {
          ...options,
          confirm_not_in_line:
            true,
        }
      );
    }


    // ==========================================
    // מעבר לכמות שהוגדרה
    // ==========================================

    if (
      data.code ===
      "OVER_EXPECTED"
    ) {
      const confirmed =
        window.confirm(
          `הגעת לכמות המשטחים שהוגדרה להזמנה.\n\n` +
          `צפי: ${data.expected}\n` +
          `הועמסו: ${data.loaded}\n\n` +
          `האם אתה בטוח שברצונך להוסיף משטח נוסף?`
        );

      if (!confirmed) {
        return null;
      }

      return requestScan(
        orderNumber,
        {
          ...options,
          confirm_overage: true,
        }
      );
    }

    return data;
  }

  // =====================================================
  // טיפול בסריקה
  // =====================================================

  async function processScan(
    orderNumber
  ) {
    setLoading(true);
    setMessage("");

    try {
      const data =
        await requestScan(
          orderNumber
        );

      // המשתמש ביטל חריגה
      if (!data) {
        setMessage(
          "הסריקה בוטלה"
        );

        return;
      }

      if (data.success) {
        setLastScan(data);

        setMessage(
          `הזמנה ${data.order_number} נקלטה בהצלחה`
        );

        await loadSummary();
      } else {
        setMessage(
          data.detail ||
          data.message ||
          "הסריקה נכשלה"
        );
      }

    } catch (error) {
      console.error(
        "Scan error:",
        error
      );

      setMessage(
        "שגיאה בתקשורת עם השרת"
      );

    } finally {
      setLoading(false);

      scanInProgressRef.current =
        false;
    }
  }

  // =====================================================
  // הזנה ידנית
  // =====================================================

  async function submitManual(e) {
    e.preventDefault();

    const value =
      manualOrder.trim();

    if (!value || loading) {
      return;
    }

    setManualOrder("");

    await processScan(value);
  }

  // =====================================================
  // המסך
  // =====================================================

  return (
    <div className="modal-backdrop">
    <div className="form-window scan-loading-window">

      <div className="form-header">
        <div>
          <div className="frame-kicker">
            ADAR Portal
          </div>

          <strong>
            העמסה בסריקה
          </strong>
        </div>

        <button
          type="button"
          onClick={onClose}
        >
          חזרה
        </button>
      </div>
        <div className="scan-loading">
            <button
                type="button"
                className="scan-loading__close"
                onClick={onClose}
                >
                ✕
            </button>
        <h1>
            העמסה בסריקה
        </h1>

        {/* סיכום */}

        <div className="scan-loading__summary">

    <div className="scan-loading__summary-card">
        <span className="scan-loading__summary-label">
        בצפי
        </span>

        <span className="scan-loading__summary-value">
        {summary.expected}
        </span>
    </div>

    <div className="scan-loading__summary-card">
        <span className="scan-loading__summary-label">
        הועמסו
        </span>

        <span className="scan-loading__summary-value">
        {summary.loaded}
        </span>
    </div>

    <div className="scan-loading__summary-card">
        <span className="scan-loading__summary-label">
        נותרו
        </span>

        <span className="scan-loading__summary-value">
        {summary.remaining}
        </span>
    </div>

    </div>

        {/* כפתור סריקה */}

        {!cameraOpen && (
            <button
            className="scan-loading__scan-button"
            onClick={startCamera}
            disabled={loading}
            >
            {loading
                ? "מעבד סריקה..."
                : "📷 סרוק משטח"}
            </button>
        )}

        {/* מצלמה */}

        {cameraOpen && (
            <div
            style={{
                marginTop: 20,
            }}
            >
            <div
                className="scan-loading__camera"
            >
                <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="scan-loading__video"
                />

                {/* מסגרת לכיוון הברקוד */}
                <div className="scan-loading__target" />

                
            </div>

            <button
                onClick={stopCamera}
                style={{
                width: "100%",
                marginTop: 10,
                fontSize: 22,
                padding: 15,
                }}
            >
                ביטול
            </button>
            </div>
        )}

        {/* הודעה */}

        {message && (
            <div
            style={{
                marginTop: 25,
                padding: 18,
                fontSize: 23,
                fontWeight: "bold",
                borderRadius: 12,
                background: "#eee",
            }}
            >
            {message}
            </div>
        )}

        {/* תוצאת הסריקה */}

        {lastScan && (
            <div
            style={{
                marginTop: 20,
                padding: 22,
                border:
                "2px solid #ccc",
                borderRadius: 16,
                fontSize: 22,
            }}
            >
            <h2>
                הזמנה{" "}
                {lastScan.order_number}
            </h2>

            <div>
                צפי:{" "}
                {lastScan.expected}
            </div>

            <div>
                הועמסו:{" "}
                {lastScan.loaded}
            </div>

            <div>
                נותרו:{" "}
                {lastScan.remaining}
            </div>
            </div>
        )}

        {/* הזנה ידנית */}

        <form
            onSubmit={submitManual}
            style={{
            marginTop: 30,
            display: "flex",
            gap: 10,
            }}
        >
            <input
            value={manualOrder}
            onChange={(e) =>
                setManualOrder(
                e.target.value
                )
            }
            placeholder="הקלד מספר הזמנה"
            style={{
                flex: 1,
                fontSize: 22,
                padding: 15,
            }}
            />

            <button
            type="submit"
            disabled={loading}
            style={{
                fontSize: 20,
                padding:
                "10px 25px",
            }}
            >
            אישור
            </button>
        </form>
        <button
        type="button"
        className="scan-loading__finish-button"
        onClick={openFinishPreview}
        disabled={
            finishing ||
            loadingFinished
        }
        >
        {finishing
            ? "מסיים העמסה..."
            : loadingFinished
            ? "✓ ההעמסה הסתיימה"
            : "🏁 סיום העמסה"}
        </button>
        {finishPreviewOpen && (
  <div className="finish-preview-backdrop">

    <div className="finish-preview-window">

      <div className="finish-preview-header">

        <div>
          <h2>סיכום העמסה</h2>

          <p>
            כל ההזמנות שנסרקו בהעמסה
          </p>
        </div>

        <button
          type="button"
          onClick={() =>
            setFinishPreviewOpen(false)
          }
        >
          ✕
        </button>

      </div>


      <div className="finish-preview-table">

        <div className="finish-preview-row finish-preview-title-row">
          <div>הזמנה</div>
          <div>בצפי</div>
          <div>הועמסו</div>
          <div>חריגות</div>
        </div>


        {finishPreviewOrders.map(
          (order) => (

            <div
              key={order.order_id}
              className={
                `finish-preview-row ${
                  order.has_exception
                    ? "finish-preview-row--error"
                    : "finish-preview-row--ok"
                }`
              }
            >

              <div>
                <strong>
                  {order.order_number}
                </strong>

                {order.customer && (
                  <small>
                    {Array.isArray(
                      order.customer
                    )
                      ? order.customer.join(", ")
                      : order.customer}
                  </small>
                )}
              </div>

              <div>
                {order.expected}
              </div>

              <div>
                {order.loaded}
              </div>

              <div>
                {order.has_exception
                  ? order.exceptions.join(
                      " | "
                    )
                  : "תקין"}
              </div>

            </div>
          )
        )}

      </div>


      <div className="finish-preview-actions">

        <button
          type="button"
          className="finish-preview-cancel"
          onClick={() =>
            setFinishPreviewOpen(false)
          }
        >
          חזרה לסריקות
        </button>

        <button
          type="button"
          className="finish-preview-confirm"
          onClick={async () => {
            setFinishPreviewOpen(false);
            await finishLoading();
          }}
        >
          ✓ אשר סיום העמסה
        </button>

      </div>

    </div>

  </div>
)}
        </div>
    </div>
    </div>
  );
}
