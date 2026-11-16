import {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  BrowserCodeReader,
  BrowserMultiFormatReader,
} from "@zxing/browser";

import {
  BarcodeFormat,
  DecodeHintType,
} from "@zxing/library";

import { API_URL } from "../config";


export default function DailyAreaScan({
  onClose,
}) {

  const [area, setArea] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [cameraOpen, setCameraOpen] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [done, setDone] =
    useState(false);

  const [error, setError] =
    useState("");

  const [successMessage, setSuccessMessage] =
    useState("");


  const videoRef =
    useRef(null);

  const controlsRef =
    useRef(null);

  const scanLockedRef =
    useRef(false);


  // =====================================================
  // טעינת האזור הבא
  // =====================================================

  async function loadNextArea() {

    setLoading(true);
    setError("");

    try {

      const response = await fetch(
        `${API_URL}/api/daily-area/next`
      );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
          "שגיאה בטעינת האזור הבא"
        );

      }


      if (data.done) {

        setDone(true);
        setArea(null);

        return;
      }


      setDone(false);
      setArea(data.area);


    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "שגיאה בטעינת האזור"
      );

    } finally {

      setLoading(false);
    }
  }


  useEffect(() => {

    loadNextArea();

  }, []);


  // =====================================================
  // סגירת מצלמה
  // =====================================================

  function stopCamera() {

    try {
      controlsRef.current?.stop();
    } catch {}


    controlsRef.current = null;


    try {
      BrowserCodeReader
        .releaseAllStreams?.();
    } catch {}


    if (videoRef.current) {

      const stream =
        videoRef.current.srcObject;


      if (stream) {

        stream
          .getTracks()
          .forEach(
            (track) =>
              track.stop()
          );
      }


      videoRef.current.srcObject =
        null;
    }


    scanLockedRef.current =
      false;

    setCameraOpen(false);
  }


  // =====================================================
  // שליחת הברקוד לשרת
  // =====================================================

  async function submitBarcode(
    barcode
  ) {

    if (!area?.id) {
      return;
    }


    setSaving(true);
    setError("");


    try {

      const response = await fetch(
        `${API_URL}/api/daily-area/scan`,
        {
          method: "PATCH",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            record_id: area.id,
            barcode:
              String(barcode).trim(),
          }),
        }
      );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
          "הברקוד אינו מתאים לאזור"
        );
      }


      try {
        navigator.vibrate?.(200);
      } catch {}


      setSuccessMessage(
        `אזור ${area.area_number} נסרק בהצלחה`
      );


      // האזור נסרק
      // מביאים מיד את הבא

      await loadNextArea();


      setTimeout(() => {

        setSuccessMessage("");

      }, 2500);


    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "שגיאה בסריקה"
      );

    } finally {

      setSaving(false);
    }
  }


  // =====================================================
  // מצלמה
  // =====================================================

  useEffect(() => {

    if (!cameraOpen) {
      return;
    }


    let cancelled = false;


    const hints =
      new Map();


    hints.set(
      DecodeHintType.POSSIBLE_FORMATS,
      [
        BarcodeFormat.CODE_128,
        BarcodeFormat.QR_CODE,
      ]
    );


    const reader =
      new BrowserMultiFormatReader(
        hints
      );


    async function startCamera() {

      try {

        scanLockedRef.current =
          false;


        const controls =
          await reader
            .decodeFromConstraints(

              {
                video: {

                  facingMode: {
                    ideal:
                      "environment",
                  },

                  width: {
                    ideal: 1280,
                  },

                  height: {
                    ideal: 720,
                  },
                },

                audio: false,
              },

              videoRef.current,

              (
                result,
                error,
                controls
              ) => {

                if (
                  cancelled ||
                  !result ||
                  scanLockedRef.current
                ) {
                  return;
                }


                const value =
                  result
                    .getText()
                    ?.trim();


                if (!value) {
                  return;
                }


                scanLockedRef.current =
                  true;


                console.log(
                  "AREA BARCODE:",
                  value
                );


                try {
                  controls.stop();
                } catch {}


                setCameraOpen(false);


                submitBarcode(
                  value
                );
              }
            );


        controlsRef.current =
          controls;


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


    startCamera();


    return () => {

      cancelled = true;

      try {
        controlsRef.current?.stop();
      } catch {}

    };

  }, [cameraOpen]);


  // =====================================================
  // UI
  // =====================================================

  return (

    <div className="modal-backdrop">

      <div className="form-window daily-area-window">


        <div className="form-header">

          <div>

            <div className="frame-kicker">
              ADAR Portal
            </div>

            <strong>
              סריקת אזורים יומית
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


        {loading && (

          <div className="form-message">
            טוען את האזור הבא...
          </div>

        )}


        {error && (

          <div className="form-error">
            {error}
          </div>

        )}


        {successMessage && (

          <div className="daily-area-success">
            ✓ {successMessage}
          </div>

        )}


        {!loading && done && (

          <div className="daily-area-done">

            <div className="daily-area-done-icon">
              ✓
            </div>

            <strong>
              כל האזורים נסרקו היום
            </strong>

          </div>

        )}


        {!loading &&
          !done &&
          area && (

          <div className="daily-area-content">


            <div className="daily-area-number">

              אזור

              <strong>
                {area.area_number}
              </strong>

            </div>


            <div className="daily-area-description">

              <span>
                האזור הבא
              </span>

              <strong>
                {area.description}
              </strong>

            </div>


            <button
              type="button"

              className="daily-area-scan-button"

              disabled={saving}

              onClick={() => {
                setError("");
                setCameraOpen(true);
              }}
            >

              {saving
                ? "שומר..."
                : "📷 סריקת ברקוד האזור"}

            </button>

          </div>

        )}


        {cameraOpen && (

          <div className="scanner-overlay">

            <div className="scanner-box">


              <div className="scanner-title">

                סרוק את הברקוד של אזור{" "}

                <strong>
                  {area?.area_number}
                </strong>

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