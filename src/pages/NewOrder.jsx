import { useEffect, useState } from "react";

import { API_URL } from "../config";

export default function NewOrder({ onClose }) {
  const [customers, setCustomers] = useState([]);
  const [agents, setAgents] = useState([]);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    order_number: "",
    customer_id: "",
    agent_id: "",
    delivery_date: "",
    picking_rows: "",
    goes_with_us: false,
    line: "",
    delivery_notes: "9:00-14:00",
    warehouse_notes: "",
    status: "לפני יצור",
    

  });
 const [showNewCustomer, setShowNewCustomer] = useState(false);
 const [newCustomer, setNewCustomer] = useState({
  customer_number: "",
  customer_name: "",
  phone: "",
  address: "",
  notes: "",
 });

  useEffect(() => {
    async function loadData() {
      const customersRes = await fetch(`${API_URL}/api/customers`);
      const agentsRes = await fetch(`${API_URL}/api/agents`);

      setCustomers(await customersRes.json());
      setAgents(await agentsRes.json());
    }

    loadData();
  }, []);

  function updateField(field, value) {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  }

  async function submit(e) {
    e.preventDefault();

    if (!form.order_number) {
      alert("חובה למלא מספר הזמנה");
      return;
    }

    if (!form.customer_id) {
      alert("חובה לבחור לקוח");
      return;
    }

    setSaving(true);

    try {
      const res = await fetch(`${API_URL}/api/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...form,
          picking_rows: form.picking_rows ? Number(form.picking_rows) : null,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        alert("שגיאה בשמירה: " + JSON.stringify(data));
        return;
      }

      alert("ההזמנה נשמרה בהצלחה");
      onClose();
    } catch (err) {
      alert("שגיאה בחיבור לשרת");
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="form-window">
        <div className="form-header">
          <div>
            <div className="frame-kicker">ADAR Portal</div>
            <strong>קליטת הזמנה חדשה</strong>
          </div>

          <button onClick={onClose}>חזרה</button>
        </div>

        <form className="order-form" onSubmit={submit}>
          <label>מספר הזמנה</label>
          <input
            value={form.order_number}
            onChange={(e) => updateField("order_number", e.target.value)}
          />
          <label>לקוח</label>
          <button
            type="button"
           className="small-add-button"
           onClick={() => setShowNewCustomer(true)}
          >
         + הוסף לקוח
         </button>

<input
  type="text"
  placeholder="הקלידי מספר לקוח או שם לקוח..."
  value={form.customer_search || ""}
  onChange={(e) => {
    updateField("customer_search", e.target.value);
    updateField("customer_id", "");
  }}
/>

{form.customer_search && !form.customer_id && (
  <div className="search-results">
    {customers
      .filter((c) =>
        `${c.number} ${c.name} ${c.display}`
          .toLowerCase()
          .includes(form.customer_search.toLowerCase())
      )
      .slice(0, 15)
      .map((c) => (
        <button
          type="button"
          key={c.id}
          className="search-option"
          onClick={() => {
            updateField("customer_id", c.id);
            updateField("customer_search", c.display);
          }}
        >
          <strong>{c.number}</strong>
          <span>{c.name}</span>
        </button>
      ))}
  </div>
)}

       

          <label>תאריך אספקה</label>
          <input
            type="date"
            value={form.delivery_date}
            onChange={(e) => updateField("delivery_date", e.target.value)}
          />

          <label>שורות ליקוט</label>
          <input
            type="number"
            value={form.picking_rows}
            onChange={(e) => updateField("picking_rows", e.target.value)}
          />

          <label>סוכן</label>
          <select
            value={form.agent_id}
            onChange={(e) => updateField("agent_id", e.target.value)}
          >
            <option value="">בחר סוכן</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>

          <label>קו אלי</label>
          <select
            value={form.line}
            onChange={(e) => updateField("line", e.target.value)}
          >
            <option value="">בחר קו</option>
            <option value="ירושלים">ירושלים</option>
            <option value="שכם">שכם</option>
            <option value="ברטעה">ברטעה</option>
          </select>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.goes_with_us}
              onChange={(e) => updateField("goes_with_us", e.target.checked)}
            />
            יוצא איתנו
          </label>

          <label>הערות אספקה</label>
          <textarea
            value={form.delivery_notes}
            onChange={(e) => updateField("delivery_notes", e.target.value)}
          />

          <label>הערות למחסן</label>
          <textarea
            value={form.warehouse_notes}
            onChange={(e) => updateField("warehouse_notes", e.target.value)}
          />

          <button className="save-button" type="submit" disabled={saving}>
            {saving ? "שומר..." : "שמור הזמנה"}
          </button>
        </form>
      </div>
      {showNewCustomer && (
  <div className="inner-modal">
    <div className="inner-card">
      <h2>הוספת לקוח חדש</h2>

      <input
        placeholder="מספר לקוח"
        value={newCustomer.customer_number}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, customer_number: e.target.value })
        }
      />

      <input
        placeholder="שם לקוח"
        value={newCustomer.customer_name}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, customer_name: e.target.value })
        }
      />

      <input
        placeholder="טלפון"
        value={newCustomer.phone}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, phone: e.target.value })
        }
      />

      <input
        placeholder="כתובת"
        value={newCustomer.address}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, address: e.target.value })
        }
      />
      <input
        placeholder="עיר"
        value={newCustomer.city}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, city: e.target.value })
        }
      />
       <label>סיגמנט</label>
       <input
       type="checkbox"
        
        value={newCustomer.sigment}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, sigment: e.target.value })
        }
      />
      <label>מיקאסה</label>
       <input
       type="checkbox"
        placeholder="מיקאסה"
        value={newCustomer.mikasa}
        onChange={(e) =>
          setNewCustomer({ ...newCustomer, mikasa: e.target.value })
        }
      />
      מ
     

    

      <div className="inner-actions">
        <button type="button" onClick={() => setShowNewCustomer(false)}>
          ביטול
        </button>

        <button
          type="button"
          onClick={async () => {
            if (!newCustomer.customer_name) {
              alert("חובה למלא שם לקוח");
              return;
            }

            const res = await fetch(`${API_URL}/api/customers`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(newCustomer),
            });

            const created = await res.json();

            if (!res.ok) {
              alert("שגיאה ביצירת לקוח: " + JSON.stringify(created));
              return;
            }

            setCustomers((prev) => [...prev, created]);

            updateField("customer_id", created.id);
            updateField("customer_search", created.display);

            setShowNewCustomer(false);
            setNewCustomer({
              customer_number: "",
              customer_name: "",
              phone: "",
              address: "",
              city:"",
              sigment:"",
              mikasa:""
             
            });
          }}
        >
          שמור לקוח
        </button>
      </div>
    </div>
  </div>
)}
    </div>
  );
}