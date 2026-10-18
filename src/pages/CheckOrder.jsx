import {
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  BrowserMultiFormatReader
} from "@zxing/browser";

import {
  BarcodeFormat,
  DecodeHintType
} from "@zxing/library";
import OrderBarcode from "./OrderBarcode";
import { API_URL } from "../config";

export default function CheckOrder({ onClose }) {
  const [orders, setOrders] = useState([]);
  const [amount, setAmount] = useState("");
   const [notes, setNotes] = useState("");
  const [invoice, setInvoince] = useState("");

  const [orderSearch, setOrderSearch] = useState("");
  const invoiceVideoRef = useRef(null);
  const invoiceControlsRef = useRef(null);

  const [
    invoiceCameraOpen,
    setInvoiceCameraOpen
  ] = useState(false);

  const invoiceScanInProgressRef =
  useRef(false);
 

  const [selectedOrder, setSelectedOrder] = useState(null);



  const [orderActiveIndex, setOrderActiveIndex] = useState(-1);


  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError("");

      try {
        const [ordersResponse] = await Promise.all([
          fetch(`${API_URL}/api/orders/filter_by_status?status=מלוקט&action=0`),
         
        ]);

        const ordersData = await ordersResponse.json();
     

        if (!ordersResponse.ok) {
          throw new Error(
            typeof ordersData.detail === "string"
              ? ordersData.detail
              : "שגיאה בטעינת ההזמנות"
          );
        }

      
        setOrders(Array.isArray(ordersData) ? ordersData : []);
     
      } catch (loadError) {
        console.error(loadError);
        setError(loadError.message || "שגיאה בטעינת הנתונים");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const filteredOrders = useMemo(() => {
    const query = orderSearch.trim().toLowerCase();

    const result = orders.filter((order) => {
      const searchableText = [
        order.order_number,
        order.customer_name,
        order.display,
        order.amount,
        order.notes,
        order.order_date,
        order.same_customer_date
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return !query || searchableText.includes(query);
    });

    return result.slice(0, 30);
  }, [orders, orderSearch]);



  function chooseOrder(order) {
    setSelectedOrder(order);
    setOrderSearch(order.display || order.order_number || "");
    setOrderActiveIndex(-1);
  }



  function handleOrderKeyDown(event) {
    if (selectedOrder) {
      if (event.key === "Escape") {
        setSelectedOrder(null);
        setOrderSearch("");
      }

      return;
    }

    if (!filteredOrders.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();

      setOrderActiveIndex((current) =>
        current < filteredOrders.length - 1 ? current + 1 : 0
      );
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();

      setOrderActiveIndex((current) =>
        current > 0 ? current - 1 : filteredOrders.length - 1
      );
    }

    if (event.key === "Enter" && orderActiveIndex >= 0) {
      event.preventDefault();
      chooseOrder(filteredOrders[orderActiveIndex]);
    }

    if (event.key === "Escape") {
      setOrderSearch("");
      setOrderActiveIndex(-1);
    }
  }

  function handleEmployeeKeyDown(event) {
    if (selectedEmployee) {
      if (event.key === "Escape") {
        setSelectedEmployee(null);
        setEmployeeSearch("");
      }

      return;
    }

    if (!filteredEmployees.length) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();

      setEmployeeActiveIndex((current) =>
        current < filteredEmployees.length - 1 ? current + 1 : 0
      );
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();

      setEmployeeActiveIndex((current) =>
        current > 0 ? current - 1 : filteredEmployees.length - 1
      );
    }

    if (event.key === "Enter" && employeeActiveIndex >= 0) {
      event.preventDefault();
      chooseEmployee(filteredEmployees[employeeActiveIndex]);
    }

    if (event.key === "Escape") {
      setEmployeeSearch("");
      setEmployeeActiveIndex(-1);
    }
  }
function stopInvoiceCamera() {
  try {
    invoiceControlsRef.current?.stop();

    if (invoiceVideoRef.current?.srcObject) {
      const tracks =
        invoiceVideoRef.current.srcObject.getTracks();

      tracks.forEach((track) => track.stop());

      invoiceVideoRef.current.srcObject = null;
    }

  } catch (error) {
    console.error(
      "Invoice camera stop error:",
      error
    );
  }

  invoiceControlsRef.current = null;
  setInvoiceCameraOpen(false);
}

async function improveCamera(videoElement) {
  try {
    const stream =
      videoElement?.srcObject;

    if (!stream) {
      return;
    }

    const track =
      stream.getVideoTracks()[0];

    if (!track) {
      return;
    }

    const capabilities =
      track.getCapabilities?.() || {};

    console.log(
      "Invoice camera capabilities:",
      capabilities
    );

    const advanced = [];

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

    if (advanced.length > 0) {
      await track.applyConstraints({
        advanced,
      });
    }

  } catch (error) {
    console.error(
      "Invoice camera enhancement error:",
      error
    );
  }
}
async function startInvoiceCamera() {
  if (invoiceCameraOpen) {
    return;
  }

  setError("");

  invoiceScanInProgressRef.current = false;

  try {
    setInvoiceCameraOpen(true);

    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(resolve);
      });
    });

    const videoElement =
      invoiceVideoRef.current;

    if (!videoElement) {
      throw new Error(
        "Invoice video element not available"
      );
    }

    const hints = new Map();

    hints.set(
  DecodeHintType.POSSIBLE_FORMATS,
  [
    BarcodeFormat.EAN_13
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

        (
  result,
  error,
  controlsFromCallback
) => {

  if (!result) {
    if (error) {
      console.log(
        "EAN13 decode error:",
        error.name,
        error.message
      );
    }

    return;
  }

  console.log(
    "EAN13 FOUND:",
    result.getText(),
    result.getBarcodeFormat()
  );

          if (
            invoiceScanInProgressRef.current
          ) {
            return;
          }

          const invoiceNumber =
            result.getText()?.trim();

          if (!invoiceNumber) {
            return;
          }

          invoiceScanInProgressRef.current =
            true;

          setInvoince(invoiceNumber);

          try {
            controlsFromCallback?.stop();
          } catch {}

          stopInvoiceCamera();
        }
      );

    invoiceControlsRef.current = controls;
    await improveCamera(videoElement);

  } catch (error) {
    console.error(
      "Invoice scan error:",
      error
    );

    stopInvoiceCamera();

    setError(
      "לא ניתן לפתוח את המצלמה לסריקת החשבונית"
    );
  }
}

  async function submit(event) {
    event.preventDefault();

    if (!selectedOrder?.id) {
      setError("חובה לבחור הזמנה");
      return;
    }

    

    setSaving(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/orders/check`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            order_id: selectedOrder.id,
            amount: amount==""?null: Number(amount),
            notes: notes==""?null :notes,
            invoice:invoice==""?null :invoice
          }),
        }
      );

      const responseData = await response.json();

      if (!response.ok) {
        let message = "שגיאה בסיום הליקוט";

        if (typeof responseData.detail === "string") {
          message = responseData.detail;
        } else if (responseData.detail) {
          message = JSON.stringify(responseData.detail, null, 2);
        }

        throw new Error(message);
      }

      alert("בדיקת הזמנה נשמרה בהצלחה");
      onClose();
    } catch (submitError) {
      console.error(submitError);
      setError(submitError.message || "שגיאה בסיום הליקוט");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="form-window picking-window">
        <div className="form-header">
          <div>
            <div className="frame-kicker">ADAR Portal</div>
            <strong> בדיקת הזמנה</strong>
          </div>

          <button type="button" onClick={onClose}>
            חזרה
          </button>
        </div>

        <form className="order-form" onSubmit={submit}>
          {loading && (
            <div className="form-message">
              טוען הזמנות ...
            </div>
          )}

          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          <div className="picker-section">
            <label>הזמנה</label>

            <input
              type="text"
              placeholder="הקלד מספר הזמנה או שם לקוח..."
              value={orderSearch}
              disabled={loading}
              autoComplete="off"
              onKeyDown={handleOrderKeyDown}
              onChange={(event) => {
                setOrderSearch(event.target.value);
                setSelectedOrder(null);
                setOrderActiveIndex(-1);
              }}
            />

            {!selectedOrder && !loading && (
              <div className="picker-results">
                {filteredOrders.length > 0 ? (
                  filteredOrders.map((order, index) => (
                    <button
                      type="button"
                      key={order.id}
                      className={`picker-row ${
                        orderActiveIndex === index ? "active" : ""
                      }`}
                      onMouseEnter={() => setOrderActiveIndex(index)}
                      onClick={() => chooseOrder(order)}
                    >
                      <div className="picker-main">
                        {order.order_number}
                      </div>

                      <div className="picker-secondary">
                        {order.customer_name || "ללא שם לקוח"}
                      </div>
                       <div className="picker-secondary">
 
                        תאריך אספקה :  {order.order_date || "ללא תאריך אספקה"}  
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="empty-search">
                     לא נמצאו הזמנות מלוקטות
                  </div>
                )}
              </div>
            )}

            {selectedOrder && (
              <div className="selected-record">
                <div>
                  <span>הזמנה שנבחרה</span>
                  <strong  style={{ whiteSpace: "pre-line" }}>{selectedOrder.display}</strong>
                       {selectedOrder.notes && (
                    <div
                        style={{
                          color: "red",
                          fontWeight: "bold",
                          marginTop: "6px",
                        }}
                      >
                        הערות: {selectedOrder.notes}
                      </div>
                  )}
                    {selectedOrder.same_customer_date && (
                    <div
                        style={{
                          color: "red",
                          fontWeight: "bold",
                          marginTop: "6px",
                        }}
                      >
                         {selectedOrder.same_customer_date}
                      </div>
                       
                  )}
                   <div style={{ marginTop: "16px", textAlign: "center" }}>
                                        <OrderBarcode value={selectedOrder.order_number} />
                   </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedOrder(null);
                    setOrderSearch("");
                  }}
                >
                  שינוי
                </button>
              </div>
            )}
          </div>
          <label>עדכון כמות</label>

            <input
                type="number"
                min="0"
                step="1"
                placeholder="הקלד מספר"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
            />
              <label>הערות</label>
            <input
                type="text"
               
                
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
            />
            <label>מספר חשבונית</label>
            <h4>יש לסרוק את ברקוד החשבונית</h4>

{!invoiceCameraOpen && (
  <>
    <button
      type="button"
      onClick={startInvoiceCamera}
      style={{
        width: "100%",
        minHeight: "58px",
        fontSize: "20px",
        fontWeight: "bold",
        cursor: "pointer",
      }}
    >
      📷 סרוק חשבונית
    </button>

    {invoice && (
      <div
        style={{
          marginTop: "12px",
          padding: "14px",
          borderRadius: "10px",
          background: "#dcfce7",
          fontSize: "20px",
          fontWeight: "bold",
          textAlign: "center",
        }}
      >
        מספר חשבונית: {invoice}

        <button
          type="button"
          onClick={() => {
            setInvoince("");
            startInvoiceCamera();
          }}
          style={{
            marginRight: "15px",
          }}
        >
          סרוק מחדש
        </button>
      </div>
    )}
  </>
)}
          {invoiceCameraOpen && (
  <div
    style={{
      marginTop: "15px",
    }}
  >
    <div
      style={{
        position: "relative",
        overflow: "hidden",
        borderRadius: "14px",
        background: "#000",
      }}
    >
      <video
        ref={invoiceVideoRef}
        autoPlay
        playsInline
        muted
        style={{
          width: "100%",
          display: "block",
        }}
      />

      <div
        style={{
    position: "absolute",
    left: "5%",
    right: "5%",
    top: "42%",
    height: "16%",
    border: "3px solid white",
    borderRadius: "10px",
    pointerEvents: "none",
}}
      />
    </div>

    <button
      type="button"
      onClick={stopInvoiceCamera}
      style={{
        width: "100%",
        marginTop: "10px",
        padding: "14px",
        fontSize: "18px",
      }}
    >
      ביטול
    </button>
  </div>
)}


          <button
            className="save-button"
            type="submit"
            disabled={
              loading ||
              saving ||
              !selectedOrder 
              
            }
          >
            {saving ? "שומר..." : "בדיקת הזמנה"}
          </button>
        </form>
      </div>
    </div>
  );
}