import { useEffect, useState } from "react";
import { API_URL } from "../config";

// Uses the shared CSS classes from EndPicking.jsx.
export default function ContainerUnloading({ onClose, user }) {
  const [tab, setTab] = useState(null);
  const [options, setOptions] = useState({ containers: [], suppliers: [], transports: [], photo_containers: [] });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ container_record_id: "", supplier_record_id: "", transport_record_id: "", driver_name: "", warehouseChoice: "", customWarehouse: "" ,truck:""});
  const [photoContainer, setPhotoContainer] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [startPhotoFile, setStartPhotoFile] = useState(null);
  const [transportOtherName, setTransportOtherName] = useState("");

  async function loadOptions() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/container-unloading/options`, { credentials: "include" });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "שגיאה בקריאת הרשומות");
      setOptions(body);
    } catch (e) { setError(e.message || "שגיאת תקשורת"); }
    finally { setLoading(false); }
  }
  useEffect(() => { loadOptions(); }, []);
  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
  const warehouse = form.warehouseChoice === "אחר" ? form.customWarehouse.trim() : form.warehouseChoice;
  const valid = Boolean(
  form.container_record_id &&
  form.supplier_record_id &&
  form.transport_record_id &&
  (
    form.transport_record_id !== "other" ||
    transportOtherName.trim()
  )  &&
  form.driver_name.trim() &&
  warehouse &&
  startPhotoFile &&
  !loading &&
  !saving
);

  async function start(event) {
    event.preventDefault();
    if (!valid) return;
    setSaving(true); setError(""); setMessage("");
    try {
        
        if (!startPhotoFile) {
        throw new Error("חובה לצלם או לבחור תמונה");
        }

        // שלב 1: העלאת התמונה
        const imageData = new FormData();
        imageData.append("file", startPhotoFile);

        const photoResponse = await fetch(
        `${API_URL}/api/container-unloading/${encodeURIComponent(
            form.container_record_id
        )}/photo`,
        {
            method: "POST",
            credentials: "include",
            body: imageData,
        }
        );

        const photoResult = await photoResponse.json().catch(() => ({}));

        if (!photoResponse.ok) {
        throw new Error(
            typeof photoResult.detail === "string"
            ? photoResult.detail
            : "שמירת צילום המכולה נכשלה"
        );
        }

// שלב 2: רק אחרי שהתמונה נשמרה, ממשיכים לבקשת start

      const response = await fetch(`${API_URL}/api/container-unloading/start`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          container_record_id: form.container_record_id,
          supplier_record_id: form.supplier_record_id,
          transport_record_id: form.transport_record_id,
          transport_other_name:
          form.transport_record_id === "other"
                ? transportOtherName.trim()
                : null,
          driver_name: form.driver_name.trim(), 
           warehouse:
            warehouse === "אחר"
            ? otherWarehouse.trim()
            : warehouse,
            employee_id: user.id,
            truck_number:form.truck

        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "תחילת הפריקה נכשלה");
      setMessage(`הפריקה התחילה. מחסן: ${body.warehouse}`);
      setPhotoContainer(form.container_record_id);
      setTab("photo");
      await loadOptions();
    } catch (e) { setError(e.message || "שגיאת תקשורת"); }
    finally { setSaving(false); }
  }

  async function uploadPhoto(event) {
    event.preventDefault();
    if (!photoContainer || !photoFile) { setError("חובה לבחור מכולה ולהעלות או לצלם תמונה"); return; }
    setError(""); setMessage(""); setSaving(true);
    try {
      const data = new FormData(); data.append("file", photoFile);
      const response = await fetch(`${API_URL}/api/container-unloading/${encodeURIComponent(photoContainer)}/photo`, {
        method: "POST", credentials: "include", body: data,
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "שמירת התמונה נכשלה");
      setMessage("התמונה נשמרה במכולה בהצלחה"); setPhotoFile(null);
    } catch (e) { setError(e.message || "שגיאת תקשורת"); }
    finally { setSaving(false); }
  }

  return (
    <div className="modal-backdrop" dir="rtl">
      <div className="form-window picking-window container-unloading">
        <div className="form-header">
          <div><div className="frame-kicker">ADAR Portal</div><strong>ניהול פריקת מכולות</strong></div>
          <button type="button" onClick={onClose}>חזרה</button>
        </div>
        <div className="order-form">
          <div className="picker-section" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            
<div className="unloading-tabs">
  <button
            type="button"
            className={`unloading-tab ${tab === "start" ? "active" : ""}`}
            onClick={() => setTab("start")}
        >
            📦 תחילת פריקה
        </button>

        <button
            type="button"
            className={`unloading-tab ${tab === "end" ? "active" : ""}`}
            onClick={() => setTab("end")}
        >
            ✅ סיום פריקה
        </button>

        <button
            type="button"
            className={`unloading-tab ${tab === "photo" ? "active" : ""}`}
            onClick={() => setTab("photo")}
        >
            📷 תיעוד וצילום
        </button>
        </div>

          </div>
          {loading && <div className="form-message">טוען נתונים...</div>}
          {error && <div className="form-error" role="alert">{error}</div>}
          {message && <div className="form-message" role="status">{message}</div>}
          {tab === "start" && (
            <form onSubmit={start} className="order-form">
              <div className="picker-section"><label>מספר מכולה (לפני פריקה)</label>
                <select required value={form.container_record_id} onChange={e => update("container_record_id", e.target.value)}>
                  <option value="">בחר מכולה</option>
                  {options.containers.map(x => <option key={x.id} value={x.id}>{x.label}</option>)}
                </select>
              </div>
                          <div className="picker-section"><label>ספק</label>
                <select required value={form.supplier_record_id} onChange={e => update("supplier_record_id", e.target.value)}>
                  <option value="">בחר ספק</option>
                  {options.suppliers.map(x => <option key={x.id} value={x.id}>{x.label || x.id}</option>)}
                </select>
              </div>


                <div className="picker-section">
                <label>חברת הובלה</label>

                <div className="picker-results">
                    {(options.transports || []).map((company) => (
                    <button
                        key={company.id}
                        type="button"
                        className={`picker-row ${
                        form.transport_record_id === company.id
                            ? "active"
                            : ""
                        }`}
                        onClick={() => {
                        update("transport_record_id", company.id);
                        setTransportOtherName("");
                        }}
                    >
                        <span className="picker-secondary">
                        {company.label || company.id}
                        </span>

                        {form.transport_record_id === company.id && "✓"}
                    </button>
                    ))}

                    <button
                    type="button"
                    className={`picker-row ${
                        form.transport_record_id === "other"
                        ? "active"
                        : ""
                    }`}
                    onClick={() =>
                        update("transport_record_id", "other")
                    }
                    >
                    <span className="picker-secondary">
                        ➕ אחר — חברת הובלה חדשה
                    </span>
                    </button>
                </div>

                {form.transport_record_id === "other" && (
                    <div className="picker-section">
                    <label>שם חברת הובלה חדשה</label>

                    <input
                        type="text"
                        required
                        maxLength={150}
                        placeholder="הזן שם חברת הובלה"
                        value={transportOtherName}
                        onChange={(e) =>
                        setTransportOtherName(e.target.value)
                        }
                    />
                    </div>
                )}
                </div>

         
              <div className="picker-section"><label>שם נהג</label><input required value={form.driver_name} onChange={e => update("driver_name", e.target.value)} placeholder="שם הנהג" /></div>
              <div className="picker-section"><label>מספר משאית</label><input required value={form.truck} onChange={e => update("truck", e.target.value)} placeholder="מספר משאית" /></div>
              <div className="picker-section"><label>מחסן</label>
                <select required value={form.warehouseChoice} onChange={e => update("warehouseChoice", e.target.value)}>
                  <option value="">בחר מחסן</option>
                  {['100', '200', '300', '600', 'אחר'].map(x => <option key={x} value={x}>{x}</option>)}
                </select>
                {form.warehouseChoice === 'אחר' && <input required maxLength={100} value={form.customWarehouse} onChange={e => update("customWarehouse", e.target.value)} placeholder="מספר או שם מחסן אחר" />}

                
<div className="picker-section">
  <label> צילום מכולה </label>

  
<div className="unloading-photo-actions">
  <label className="unloading-photo-button">
    <span>📷 פתח מצלמה</span>
    <input
      type="file"
      accept="image/*"
      capture="environment"
      onChange={(e) =>
        setStartPhotoFile(e.target.files?.[0] || null)
      }
    />
  </label>

  <label className="unloading-photo-button">
    <span>📁 בחר תמונה מהמכשיר</span>
    <input
      type="file"
      accept="image/*"
      onChange={(e) =>
        setStartPhotoFile(e.target.files?.[0] || null)
      }
    />
  </label>
</div>


    {startPhotoFile ? (
        <div className="form-message">
        ✅ נבחרה תמונה: {startPhotoFile.name}
        </div>
    ) : (
        <div className="form-error">
        </div>
    )}
    </div>


              </div>
              <button type="submit" className="save-button" disabled={!valid}>{saving ? 'שומר...' : 'אישור תחילת פריקה'}</button>
            </form>
          )}
          {tab === "end" && <div className="form-message">טופס סיום פריקה יוגדר בהמשך לפי ההנחיות שלך. לא מתבצע עדכון נתונים.</div>}
          {tab === "photo" && (
            <form onSubmit={uploadPhoto} className="order-form">
              <div className="picker-section"><label>מכולה לתיעוד</label>
                <select required value={photoContainer} onChange={e => setPhotoContainer(e.target.value)}>
                  <option value="">בחרי מכולה</option>
                  {options.photo_containers.map(x => <option key={x.id} value={x.id}>{x.label}</option>)}
                </select>
              </div>
              <div className="picker-section"><label>פתיחת מצלמה או בחירת תמונה</label>
                <input type="file" accept="image/*" capture="environment" required onChange={e => setPhotoFile(e.target.files?.[0] || null)} />
                <div className="form-message">בטלפון: ניתן לפתוח מצלמה. במחשב: ניתן לבחור קובץ תמונה. אי אפשר לשלוח בלי תמונה.</div>
              </div>
              <button type="submit" className="save-button" disabled={!photoContainer || !photoFile || saving}>{saving ? 'מעלה...' : 'שמירת התמונה'}</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

