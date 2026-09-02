import { useEffect, useMemo, useState } from "react";
import { API_URL } from "../config";
export default function LoadingOrders({ onClose,user}) {
  const [orders, setOrders] = useState([]);
  const [selectedOrders, setSelectedOrders] = useState({});

  const [search, setSearch] = useState("");
  const [selectedLine, setSelectedLine] = useState("");
  const [palletAmounts, setPalletAmounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
    const params = new URLSearchParams({
  status: "בבדיקה",
  action: 1,
  user_id: user.id,
});
  useEffect(() => {
    async function loadOrders() {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(
          `${API_URL}/api/orders/filter_by_status?${params}`
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
    const sameLine =
      String(order.line || "") === String(selectedLine || "");

    if (!sameLine) {
      return false;
    }

    const searchableText = [
      order.order_number,
      order.customer_name,
      order.display,
      order.amount,
      order.order_status,
      order.line,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return !query || searchableText.includes(query);
  });
}, [orders, search, selectedLine]);
const distributionLines = useMemo(() => {
  return [
    ...new Set(
      orders
        .map((order) => order.line)
        .filter(Boolean)
    ),
  ];
}, [orders]);
useEffect(() => {
  if (!selectedLine && distributionLines.length > 0) {
    setSelectedLine(distributionLines[0]);
  }
}, [distributionLines, selectedLine]);
const totalAmount = useMemo(() => {
  return filteredOrders.reduce(
    (sum, order) => sum + (Number(order.amount) || 0),
    0
  );
}, [filteredOrders]);

function toggleOrder(order) {
  // אם ההזמנה כבר מסומנת - פשוט מבטלים בחירה
  if (selectedOrders[order.id]) {
    setSelectedOrders((current) => {
      const next = { ...current };
      delete next[order.id];
      return next;
    });

    return;
  }

  // אם בוחרים הזמנה חדשה - מבקשים אישור
  const confirmed = window.confirm(
    `האם את בטוחה שהעמסת את ההזמנה?\n\n` +
    `מספר הזמנה: ${order.order_number}\n` +
    `לקוח: ${order.customer_name || "ללא שם לקוח"}`
  );

  if (!confirmed) {
    return;
  }

  setSelectedOrders((current) => ({
    ...current,
    [order.id]: {
      id: order.id,
      order_number: order.order_number,
      customer_name: order.customer_name,
      notes: "",
      file: null,
    },
  }));
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
  function updatePalletAmount(orderId, value) {
  setPalletAmounts((current) => ({
    ...current,
    [orderId]: value,
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
  if (filteredOrders.length === 0) {
    alert("אין הזמנות לבחירה בקו הזה");
    return;
  }

  const totalPallets = filteredOrders.reduce(
    (sum, order) => sum + (Number(order.amount) || 0),
    0
  );

  const confirmed = window.confirm(
    `האם אתה בטוח שאתה רוצה לבחור את כל ההזמנות של קו ${selectedLine}?\n\n` +
    `סה"כ הזמנות: ${filteredOrders.length}\n` +
    `סה"כ משטחים: ${totalPallets}`
  );

  if (!confirmed) {
    return;
  }

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
function selectDistributionLine(line) {
  setSelectedLine(line);

  if (!line) {
    return;
  }

  const lineOrders = orders.filter(
    (order) => String(order.line) === String(line)
  );

  if (lineOrders.length === 0) {
    alert("לא נמצאו הזמנות בקו ההפצה הזה");
    return;
  }

  const confirmed = window.confirm(
    `האם להעמיס את כל ההזמנות של קו ${line}?\n\n` +
    `סה"כ ${lineOrders.length} הזמנות`
  );

  if (!confirmed) {
    return;
  }

  const next = {};

  lineOrders.forEach((order) => {
    next[order.id] = {
      id: order.id,
      order_number: order.order_number,
      customer_name: order.customer_name,
      notes: "",
      file: null,
    };
  });

  setSelectedOrders(next);
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
        amount: Number(
          palletAmounts[order.id] ??
          orders.find((item) => item.id === order.id)?.amount ??
          0
        ),
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

const selectedTotalAmount = useMemo(() => {
  return orders
    .filter((order) => selectedOrders[order.id])
    .reduce(
      (sum, order) => sum + (Number(order.amount) || 0),
      0
    );
}, [orders, selectedOrders]);

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
          <div className="distribution-tabs">
  {distributionLines.map((line) => (
    <button
      key={line}
      type="button"
      className={`distribution-tab ${
        selectedLine === line ? "active" : ""
      }`}
      onClick={() => {
        setSelectedLine(line);
        setSearch("");

        // חשוב:
        // מעבר קו לא מסמן שום הזמנה
        setSelectedOrders({});
      }}
    >
      {line}
    </button>
  ))}
</div>


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
                <div className="selected-count">
                 סה"כ משטחים: <strong>{totalAmount}</strong>
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
                        <span style={{ whiteSpace: "pre-line" }}>
                             {order.amount} משטחים
                        </span>
                         <span style={{ whiteSpace: "pre-line" }}>
                             {order.line} 
                        </span>
                        <span
                          style={{
                            color: order.order_status === "לא נבדק" ? "red" : "inherit",
                            fontWeight: order.order_status === "לא נבדק" ? "bold" : "normal",whiteSpace: "pre-line"
                          }}
                        >
                          {order.order_status}
                        </span>
                      </label>
                      
  
                      {selected && (
                        <div className="loading-order-details">
                          <label>
                            הערות להזמנה
                          </label>

                          <textarea
                            placeholder="הקלד הערות להזמנה הזאת..."
                            value={selected.notes}
                            onChange={(event) =>
                              updateOrderNotes(
                                order.id,
                                event.target.value
                              )
                            }
                          />
                          <div className="pallet-input-wrapper">
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={
                                palletAmounts[order.id] ?? order.amount ?? 0
                              }
                              onChange={(event) =>
                                updatePalletAmount(
                                  order.id,
                                  event.target.value
                                )
                              }
                              onClick={(event) =>
                                event.stopPropagation()
                              }
                            />

                            <span>עדכון משטחים</span>
                          </div>

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
            : `העמס ${selectedCount} הזמנות | סה"כ ${selectedTotalAmount} משטחים`}
        </button>
        </form>
      </div>
    </div>
  );
}