import { useEffect, useRef, useState } from "react";

const API_URL =
  import.meta.env.VITE_API_URL || "https://adar-portal-85ch.onrender.com";

export default function EmployeeSwitcher({ currentUser, onSwitchUser }) {
  const [open, setOpen] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [switchingId, setSwitchingId] = useState(null);
  const wrapperRef = useRef(null);

  // סגירה בלחיצה מחוץ לתפריט
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function openMenu() {
    setOpen((prev) => !prev);

    if (!open && employees.length === 0) {
      setLoading(true);
      setError("");

      try {
        const response = await fetch(`${API_URL}/api/users?role=warehouse`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "שגיאה בטעינת עובדים");
        }

        setEmployees(data.users || []);
      } catch (err) {
        setError(err.message || "שגיאה בטעינת עובדים");
      } finally {
        setLoading(false);
      }
    }
  }

  async function handleSelect(employee) {
    if (employee.id === currentUser.id) {
      setOpen(false);
      return;
    }

    setSwitchingId(employee.id);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/quick-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: employee.id }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "לא ניתן להחליף משתמש");
      }

      // בתוך handleSelect, אחרי קבלת data מהשרת:
    localStorage.setItem("adarUser", JSON.stringify(data.user)); // adarUser, לא portal_user
    onSwitchUser(data.user);
    setOpen(false);
    } catch (err) {
      setError(err.message || "שגיאה בהחלפת משתמש");
    } finally {
      setSwitchingId(null);
    }
  }

  return (
    <div className="employee-switcher" ref={wrapperRef}>
      <button
        type="button"
        className="employee-switcher-button"
        onClick={openMenu}
        title="החלפת משתמש מהיר"
      >
        🔄
      </button>

      {open && (
        <div className="employee-switcher-panel">
          <div className="employee-switcher-title">מעבר בין מחסנאים</div>

          {loading && (
            <div className="employee-switcher-loading">טוען...</div>
          )}

          {error && <div className="employee-switcher-error">{error}</div>}

          {!loading && !error && employees.length === 0 && (
            <div className="employee-switcher-empty">
              לא נמצאו עובדי מחסן
            </div>
          )}

          <div className="employee-switcher-list">
            {employees.map((employee) => (
              <button
                key={employee.id}
                type="button"
                className={
                  "employee-switcher-item" +
                  (employee.id === currentUser.id ? " active" : "")
                }
                disabled={switchingId !== null}
                onClick={() => handleSelect(employee)}
              >
                <span className="employee-switcher-avatar">
                  {employee.name?.[0] || "?"}
                </span>
                <span>
                  {switchingId === employee.id ? "מתחבר..." : employee.name}
                </span>
                {employee.id === currentUser.id && (
                  <span className="employee-switcher-current">נוכחי</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}