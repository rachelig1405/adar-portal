import { useEffect, useMemo, useState } from "react";

import { API_URL } from "../config";
import OrderBarcode from "./OrderBarcode";

export default function NewPicking({ onClose,user }) {
  const [orders, setOrders] = useState([]);
  

  const [orderSearch, setOrderSearch] = useState("");

  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  const [orderActiveIndex, setOrderActiveIndex] = useState(-1);
  const [employeeActiveIndex, setEmployeeActiveIndex] = useState(-1);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
  let cancelled = false;

  async function loadOrders() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/orders/filter_by_status?status=לפני יצור&action=0&user_id=${user.id}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "שגיאה בטעינת ההזמנות"
        );
      }

      if (!cancelled) {
        setOrders(Array.isArray(data) ? data : []);
      }

    } catch (err) {
      console.error(err);

      if (!cancelled) {
        setError(err.message || "שגיאה בטעינת ההזמנות");
      }

    } finally {
      if (!cancelled) {
        setLoading(false);
      }
    }
  }


  async function checkActivePicking() {
    try {
      const response = await fetch(
        `${API_URL}/api/orders/filter_by_status?status=בליקוט&action=2&user_id=${user.id}`
      );

      const data = await response.json();

      if (
        response.ok &&
        Array.isArray(data) &&
        data.length > 0
      ) {
        alert(
          `יש לך כבר הזמנה בליקוט:\n\n${data[0].display}`
        );
      }

    } catch (err) {
      console.error(
        "Error checking active picking:",
        err
      );
    }
  }


  loadOrders();

  // לא מעכב את טעינת המסך
  checkActivePicking();


  return () => {
    cancelled = true;
  };

}, [user.id]);

  const filteredOrders = useMemo(() => {
    const query = orderSearch.trim().toLowerCase();

    const result = orders.filter((order) => {
      const searchableText = [
        order.order_number,
        order.customer_name,
        order.display,
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
        `${API_URL}/api/orders/start-picking`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            order_id: selectedOrder.id,
            employee_id: user.id,
          }),
        }
      );

      const responseData = await response.json();

      if (!response.ok) {
        let message = "שגיאה בתחילת הליקוט";

        if (typeof responseData.detail === "string") {
          message = responseData.detail;
        } else if (responseData.detail) {
          message = JSON.stringify(responseData.detail, null, 2);
        }

        throw new Error(message);
      }

      alert("תחילת הליקוט נשמרה בהצלחה");
      onClose();
    } catch (submitError) {
      console.error(submitError);
      setError(submitError.message || "שגיאה בתחילת הליקוט");
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
            <strong>תחילת ליקוט</strong>
          </div>

          <button type="button" onClick={onClose}>
            חזרה
          </button>
        </div>

        <form className="order-form" onSubmit={submit}>
          {loading && (
            <div className="form-message">
              טוען הזמנות ועובדים...
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
                    לא נמצאו הזמנות בסטטוס לפני ייצור
                  </div>
                )}
              </div>
            )}

            {selectedOrder && (
              <div className="selected-record">
                <div>
                  <span>הזמנה שנבחרה</span>
                  <strong style={{ whiteSpace: "pre-line" }}>{selectedOrder.display}</strong>
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

    

          <button
            className="save-button"
            type="submit"
            disabled={
              loading ||
              saving ||
              !selectedOrder 
              
            }
          >
            {saving ? "שומר..." : "התחל ליקוט"}
          </button>
        </form>
      </div>
    </div>
  );
}