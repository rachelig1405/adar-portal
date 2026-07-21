import { useEffect, useMemo, useState } from "react";

import { API_URL } from "../config";
export default function EndPicking({ onClose }) {
  const [orders, setOrders] = useState([]);
  const [amount, setAmount] = useState("");
   const [notes, setNotes] = useState("");
   const [invoice, setInvoince] = useState("");

  const [orderSearch, setOrderSearch] = useState("");
 

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
          fetch(`${API_URL}/api/orders/filter_by_status?status=בליקוט`),
         
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
        `${API_URL}/api/orders/end-picking`,
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

      alert("סיום הליקוט נשמרה בהצלחה");
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
                    </button>
                  ))
                ) : (
                  <div className="empty-search">
                     לא נמצאו הזמנות בליקוט
                  </div>
                )}
              </div>
            )}

            {selectedOrder && (
              <div className="selected-record">
                <div>
                  <span>הזמנה שנבחרה</span>
                  <strong>{selectedOrder.display}</strong>
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
          <label>כמות</label>

            <input
                type="number"
                min="0"
                step="1"
                placeholder="הקליד מספר"
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
            <input
                type="text"
               
                
                value={invoice}
                onChange={(event) => setInvoince(event.target.value)}
            />
          


          <button
            className="save-button"
            type="submit"
            disabled={
              loading ||
              saving ||
              !selectedOrder 
              
            }
          >
            {saving ? "שומר..." : "סיום ליקוט"}
          </button>
        </form>
      </div>
    </div>
  );
}