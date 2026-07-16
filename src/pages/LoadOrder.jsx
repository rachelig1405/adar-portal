import { useEffect, useMemo, useState } from "react";
import { API_URL } from "../config";
export default function LoadingOrders({ onClose }) {
  const [orders, setOrders] = useState([]);
  const [selectedOrders, setSelectedOrders] = useState({});

  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadOrders() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(
          `${API_URL}/api/orders/filter_by_status?status=בבדיקה`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            typeof data.detail === "string"
              ? data.detail
              : "שגיאה בטעינת ההזמנות"
          );
        }

        setOrders(Array.isArray(data) ? data : []);
      } catch (loadError) {
        console.error(loadError);
        setError(loadError.message || "לא ניתן לטעון הזמנות");
      } finally {
        setLoading(false);
      }
    }

    loadOrders();
  }, []);

  const filteredOrders = useMemo(() => {
    const query = search.trim().toLowerCase();

    return orders.filter((order) => {
      const searchableText = [
        order.order_number,
        order.customer_name,
        order.display,
        order.amount
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return !query || searchableText.includes(query);
    });
  }, [orders, search]);

  function toggleOrder(order) {
    setSelectedOrders((current) => {
      const next = { ...current };

      if (next[order.id]) {
        delete next[order.id];
      } else {
        next[order.id] = {
          id: order.id,
          order_number: order.order_number,
          customer_name: order.customer_name,
          notes: "",
          file: null,
        };
      }

      return next;
    });
  }

  function updateOrderNotes(orderId, notes) {
    setSelectedOrders((current) => ({
      ...current,
      [orderId]: {
        ...current[orderId],
        notes,
      },
    }));
  }

  function updateOrderFile(orderId, file) {
    setSelectedOrders((current) => ({
      ...current,
      [orderId]: {
        ...current[orderId],
        file,
      },
    }));
  }

  function selectAllVisible() {
    setSelectedOrders((current) => {
      const next = { ...current };

      filteredOrders.forEach((order) => {
        if (!next[order.id]) {
          next[order.id] = {
            id: order.id,
            order_number: order.order_number,
            customer_name: order.customer_name,
            notes: "",
            file: null,
          };
        }
      });

      return next;
    });
  }

  function clearAllSelections() {
    setSelectedOrders({});
  }

async function submit(event) {
  event.preventDefault();

  const selectedList = Object.values(selectedOrders);

  if (selectedList.length === 0) {
    setError("חובה לבחור לפחות הזמנה אחת");
    return;
  }

  setSaving(true);
  setError("");

  try {
    // שלב 1: עדכון כל ההזמנות וההערות
    const updateResponse = await fetch(
      `${API_URL}/api/orders/loading`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          orders: selectedList.map((order) => ({
            order_id: order.id,
            notes: order.notes?.trim() || "",
          })),
        }),
      }
    );

    const updateData = await updateResponse.json();

    if (!updateResponse.ok) {
      throw new Error(
        typeof updateData.detail === "string"
          ? updateData.detail
          : JSON.stringify(updateData.detail || updateData)
      );
    }

    // שלב 2: העלאת קובץ נפרד לכל הזמנה
    const uploadErrors = [];

    for (const order of selectedList) {
      if (!order.file) {
        continue;
      }

      const formData = new FormData();

      formData.append("order_id", order.id);
      formData.append("file", order.file);

      const uploadResponse = await fetch(
        `${API_URL}/api/orders/upload-file`,
        {
          method: "PATCH",
          body: formData,
        }
      );

      const uploadData = await uploadResponse.json();

      if (!uploadResponse.ok) {
        uploadErrors.push({
          orderNumber: order.order_number,
          error:
            typeof uploadData.detail === "string"
              ? uploadData.detail
              : JSON.stringify(uploadData.detail || uploadData),
        });
      }
    }

    if (uploadErrors.length > 0) {
      const failedOrders = uploadErrors
        .map(
          (item) =>
            `${item.orderNumber}: ${item.error}`
        )
        .join("\n");

      alert(
        `ההזמנות עודכנו, אבל חלק מהקבצים לא הועלו:\n${failedOrders}`
      );
    } else {
      alert(
        `${updateData.updated_count ?? selectedList.length} הזמנות עודכנו בהצלחה`
      );
    }

    onClose();
  } catch (submitError) {
    console.error(submitError);

    setError(
      submitError.message || "שגיאה בעדכון ההעמסה"
    );
  } finally {
    setSaving(false);
  }
}

  const selectedCount = Object.keys(selectedOrders).length;

  return (
    <div className="modal-backdrop">
      <div className="form-window loading-orders-window">
        <div className="form-header">
          <div>
            <div className="frame-kicker">ADAR Portal</div>
            <strong>העמסת הזמנות</strong>
          </div>

          <button type="button" onClick={onClose}>
            חזרה
          </button>
        </div>

        <form className="order-form" onSubmit={submit}>
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

          <label>חיפוש הזמנה</label>

          <input
            type="text"
            placeholder="הקלד מספר הזמנה או שם לקוח..."
            value={search}
            disabled={loading}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />

          {!loading && (
            <>
              <div className="bulk-actions">
                <button
                  type="button"
                  onClick={selectAllVisible}
                >
                  בחר את כל התוצאות
                </button>

                <button
                  type="button"
                  className="clear-selection-button"
                  onClick={clearAllSelections}
                  disabled={selectedCount === 0}
                >
                  בטל בחירה
                </button>

                <div className="selected-count">
                  נבחרו <strong>{selectedCount}</strong> הזמנות
                </div>
              </div>

              <div className="loading-orders-list">
                {filteredOrders.map((order) => {
                  const selected = selectedOrders[order.id];

                  return (
                    <div
                      key={order.id}
                      className={`loading-order-card ${
                        selected ? "selected" : ""
                      }`}
                    >
                      <label className="loading-order-header">
                        <input
                          type="checkbox"
                          checked={Boolean(selected)}
                          onChange={() => toggleOrder(order)}
                        />

                        <strong>
                          {order.order_number}
                        </strong>

                        <span>
                          {order.customer_name ||
                            "ללא שם לקוח"}
                        </span>
                      </label>

                      {selected && (
                        <div className="loading-order-details">
                          <label>
                            הערות להזמנה
                          </label>

                          <textarea
                            placeholder="הקלידי הערות להזמנה הזאת..."
                            value={selected.notes}
                            onChange={(event) =>
                              updateOrderNotes(
                                order.id,
                                event.target.value
                              )
                            }
                          />

                          <label>
                            קובץ או תמונה להזמנה
                          </label>

                          <input
                            type="file"
                            accept="image/*,.pdf"
                            onChange={(event) =>
                              updateOrderFile(
                                order.id,
                                event.target.files?.[0] ||
                                  null
                              )
                            }
                          />

                          {selected.file && (
                            <div className="selected-file">
                              <div>
                                <strong>
                                  {selected.file.name}
                                </strong>

                                <span>
                                  {Math.ceil(
                                    selected.file.size / 1024
                                  )}{" "}
                                  KB
                                </span>
                              </div>

                              <button
                                type="button"
                                onClick={() =>
                                  updateOrderFile(
                                    order.id,
                                    null
                                  )
                                }
                              >
                                הסר
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}

          <button
            className="save-button"
            type="submit"
            disabled={
              loading ||
              saving ||
              selectedCount === 0
            }
          >
            {saving
              ? "מעדכן הזמנות..."
              : `העמס ${selectedCount} הזמנות`}
          </button>
        </form>
      </div>
    </div>
  );
}