import {
  useEffect,
  useRef,
  useState,
} from "react";

import { API_URL } from "../config";


function getToday() {
  const now = new Date();

  const year =
    now.getFullYear();

  const month =
    String(
      now.getMonth() + 1
    ).padStart(2, "0");

  const day =
    String(
      now.getDate()
    ).padStart(2, "0");

  return `${year}-${month}-${day}`;
}


export default function ForecastOrders({
  onClose,
}) {

  const [selectedDate, setSelectedDate] =
    useState("");

  const [orders, setOrders] =
    useState([]);

  const [summary, setSummary] =
    useState({
      orders: 0,
      unpicked_lines: 0,
      pallets: 0,
    });

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const dateInputRef =
    useRef(null);


  useEffect(() => {

    const controller =
      new AbortController();


    async function loadOrders() {

      setLoading(true);
      setError("");

      try {

        const response =
          await fetch(
            `${API_URL}/api/orders/forecast?date=${selectedDate}`,
            {
              signal:
                controller.signal,
            }
          );


        const data =
          await response.json();


        if (!response.ok) {
          throw new Error(
            data.detail ||
            "שגיאה בטעינת ההזמנות"
          );
        }


        setOrders(
          Array.isArray(data.orders)
            ? data.orders
            : []
        );


        setSummary(
          data.summary || {
            orders: 0,
            unpicked_lines: 0,
            pallets: 0,
          }
        );


      } catch (err) {

        if (
          err.name ===
          "AbortError"
        ) {
          return;
        }

        console.error(err);

        setError(
          err.message ||
          "שגיאה בטעינת הנתונים"
        );

      } finally {

        if (
          !controller.signal.aborted
        ) {
          setLoading(false);
        }
      }
    }


    loadOrders();


    return () =>
      controller.abort();

  }, [selectedDate]);


  function openCalendar() {

    if (
      dateInputRef.current
        ?.showPicker
    ) {
      dateInputRef.current
        .showPicker();

      return;
    }

    dateInputRef.current
      ?.click();
  }


  const formattedDate =
    new Date(
      `${selectedDate}T12:00:00`
    ).toLocaleDateString(
      "he-IL",
      {
        weekday: "long",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      }
    );


  return (
    <div className="modal-backdrop">

      <div className="form-window forecast-orders-window">

        <div className="form-header">

          <div>
            <div className="frame-kicker">
              ADAR Portal
            </div>

            <strong>
              הזמנות בצפי
            </strong>
          </div>


          <button
            type="button"
            onClick={onClose}
          >
            חזרה
          </button>

        </div>


        <div className="forecast-top">

          <div className="forecast-main-stat">

            <span>
              סה״כ שורות לא מלוקטות
            </span>

            <strong>
              {summary.unpicked_lines}
            </strong>

          </div>


          <div className="forecast-date-area">

            <button
              type="button"
              className="forecast-date-button"
              onClick={openCalendar}
            >
              📅 {formattedDate}
            </button>


            <input
              ref={dateInputRef}
              type="date"
              value={selectedDate}

              onChange={(event) =>
                setSelectedDate(
                  event.target.value
                )
              }

              className="forecast-hidden-date"
            />

          </div>

        </div>


        <div className="forecast-summary-row">

          <div>
            <span>
              הזמנות בצפי
            </span>

            <strong>
              {summary.orders}
            </strong>
          </div>


          <div>
            <span>
              סה״כ משטחים
            </span>

            <strong>
              {summary.pallets}
            </strong>
          </div>

        </div>


        {loading && (
          <div className="form-message">
            טוען הזמנות...
          </div>
        )}


        {error && (
          <div className="form-error">
            {error}
          </div>
        )}


        {!loading && (
          <div className="forecast-table-wrapper">

            <table className="forecast-table">

              <thead>
                <tr>
                  <th>
                    מספר הזמנה
                  </th>

                  <th>
                    שם לקוח
                  </th>

                  <th>
                    סטטוס
                  </th>

                  <th>
                    שורות ליקוט
                  </th>

                  <th>
                    כמות משטחים
                  </th>
                </tr>
              </thead>


              <tbody>

                {orders.map(
                  (order) => (

                    <tr key={order.id}>

                      <td className="forecast-order-number">
                        {order.order_number}
                      </td>


                      <td>
                        {order.customer_name}
                      </td>


                      <td>
                        <span
                          className={
                            `forecast-status status-${order.status}`
                          }
                        >
                          {order.status}
                        </span>
                      </td>


                      <td>
                        {order.picking_lines}
                      </td>


                      <td>
                        {order.pallets}
                      </td>

                    </tr>

                  )
                )}


                {!orders.length && (
                  <tr>
                    <td
                      colSpan="5"
                      className="forecast-empty"
                    >
                      אין הזמנות בצפי בתאריך זה
                    </td>
                  </tr>
                )}

              </tbody>

            </table>

          </div>
        )}

      </div>

    </div>
  );
}