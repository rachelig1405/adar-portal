import { useEffect, useRef } from "react";
import JsBarcode from "jsbarcode";

export default function OrderBarcode({ value }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!value || !canvasRef.current) {
      return;
    }

    try {
      JsBarcode(canvasRef.current, String(value), {
        format: "CODE128",
        width: 2,
        height: 60,
        displayValue: true,
        fontSize: 16,
        margin: 8,
      });
    } catch (error) {
      console.error("שגיאה ביצירת ברקוד:", error);
    }
  }, [value]);

  if (!value) {
    return null;
  }

  return <canvas ref={canvasRef} />;
}