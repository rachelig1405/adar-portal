import { useEffect, useMemo, useState } from "react";

import { API_URL } from "../config";

export default function NewPicking({ onClose }) {
  const [orders, setOrders] = useState([]);
  const [employees, setEmployees] = useState([]);

  const [orderSearch, setOrderSearch] = useState("");
  const [employeeSearch, setEmployeeSearch] = useState("");

  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  const [orderActiveIndex, setOrderActiveIndex] = useState(-1);
  const [employeeActiveIndex, setEmployeeActiveIndex] = useState(-1);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError("");

      try {
        const [ordersResponse, employeesResponse] = await Promise.all([
          fetch(`${API_URL}/api/orders/filter_by_status?status=לפני יצור`),
          fetch(`${API_URL}/api/employees`),
        ]);

        const ordersData = await ordersResponse.json();
        const employeesData = await employeesResponse.json();

        if (!ordersResponse.ok) {
          throw new Error(
            typeof ordersData.detail === "string"
              ? ordersData.detail
              : "שגיאה בטעינת ההזמנות"
          );
        }

        if (!employeesResponse.ok) {
          throw new Error(
            typeof employeesData.detail === "string"
              ? employeesData.detail
              : "שגיאה בטעינת העובדים"
          );
        }

        setOrders(Array.isArray(ordersData) ? ordersData : []);
        setEmployees(Array.isArray(employeesData) ? employeesData : []);
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

  const filteredEmployees = useMemo(() => {
    const query = employeeSearch.trim().toLowerCase();

    const result = employees.filter((employee) =>
      String(employee.name || "")
        .toLowerCase()
        .includes(query)
    );

    return result.slice(0, 30);
  }, [employees, employeeSearch]);

  function chooseOrder(order) {
    setSelectedOrder(order);
    setOrderSearch(order.display || order.order_number || "");
    setOrderActiveIndex(-1);
  }

  function chooseEmployee(employee) {
    setSelectedEmployee(employee);
    setEmployeeSearch(employee.name || "");
    setEmployeeActiveIndex(-1);
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

    if (!selectedEmployee?.id) {
      setError("חובה לבחור עובד");
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
            employee_id: selectedEmployee.id,
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

          <div className="picker-section">
            <label>עובד</label>

            <input
              type="text"
              placeholder="הקלידי שם עובד..."
              value={employeeSearch}
              disabled={loading}
              autoComplete="off"
              onKeyDown={handleEmployeeKeyDown}
              onChange={(event) => {
                setEmployeeSearch(event.target.value);
                setSelectedEmployee(null);
                setEmployeeActiveIndex(-1);
              }}
            />

            {!selectedEmployee && !loading && (
              <div className="picker-results employee-results">
                {filteredEmployees.length > 0 ? (
                  filteredEmployees.map((employee, index) => (
                    <button
                      type="button"
                      key={employee.id}
                      className={`picker-row ${
                        employeeActiveIndex === index ? "active" : ""
                      }`}
                      onMouseEnter={() =>
                        setEmployeeActiveIndex(index)
                      }
                      onClick={() => chooseEmployee(employee)}
                    >
                      <div className="picker-main">
                        {employee.name}
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="empty-search">
                    לא נמצאו עובדים
                  </div>
                )}
              </div>
            )}

            {selectedEmployee && (
              <div className="selected-record">
                <div>
                  <span>עובד שנבחר</span>
                  <strong>{selectedEmployee.name}</strong>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedEmployee(null);
                    setEmployeeSearch("");
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
              !selectedOrder ||
              !selectedEmployee
            }
          >
            {saving ? "שומר..." : "התחל ליקוט"}
          </button>
        </form>
      </div>
    </div>
  );
}