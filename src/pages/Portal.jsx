import { useMemo, useState } from "react";

import Logo from "../components/Logo";
import ActionCard from "../components/ActionCard";
import FrameWindow from "../components/FrameWindow";

import { getMenu } from "../data/menus";
import { useChat } from "./ChatContext";

import NewOrder from "./NewOrder";
import NewPicking from "./NewPicking";
import CheckOrder from "./CheckOrder";
import LoadingOrders from "./LoadOrder";
import EndPicking from "./EndPicking";
import ImportOrdersExcel from "./importOrdersExcel.";
import CreateProductPdfs from "./CreateStickers";
import TodayLabelsPrint from "./TodayLabels";
import UpdateInvoice from "./UpdateInvoice";
import GeneralChat from "./GeneralChat";
import PickingSummary from "./PickingSummary ";
import EmployeeSwitcher from "./EmployeeSwitcher";
import Timelock from "./TimeClock"

const INTERNAL_COMPONENTS = {
  newOrder: NewOrder,
  startPicking: NewPicking,
  endPicking: EndPicking,
  check: CheckOrder,
  loading: LoadingOrders,
  importOrdersExcel: ImportOrdersExcel,
  stickers: CreateProductPdfs,
  OrderStickers: TodayLabelsPrint,
  generalChat: GeneralChat,
  UpdateInvoice: UpdateInvoice,

};

function getRoleTitle(role) {
  const roleTitles = {
    warehouse: "מחסנאי",
    office: "משרד",
    manager: "מנהל מחסן",
    admin: "מנהל מערכת",
  };

  return roleTitles[role] || "עובד";
}
import { API_URL } from "../config"; // אם עדיין לא מיובא

// בתוך הקומפוננטה Portal:


export default function Portal({ user, onLogout ,onSwitchUser}) {
  const [activeAction, setActiveAction] = useState(null);
  const { unreadCount } = useChat();

  const menu = useMemo(() => {
    return getMenu(user.role);
  }, [user.role]);

  const activeMenuItem = useMemo(() => {
    if (!activeAction) {
      return null;
    }

    return menu.find((item) => item.key === activeAction) || null;
  }, [activeAction, menu]);

  const normalizedRole = String(user?.role || "")
    .trim()
    .toLowerCase();

  const isWarehouse = normalizedRole === "warehouse";

  const ActiveInternalComponent =
    activeAction && INTERNAL_COMPONENTS[activeAction]
      ? INTERNAL_COMPONENTS[activeAction]
      : null;

  async function handleTimeClockAction() {
  try {
    const statusResponse = await fetch(
      `${API_URL}/api/attendance/status?userId=${user.id}`
    );

    const statusData = await statusResponse.json();

    if (!statusResponse.ok) {
      alert(statusData.detail || "שגיאה בטעינת סטטוס נוכחות");
      return;
    }

    if (statusData.status === "clocked_out") {
      alert("כבר סיימת את יום העבודה היום");
      return;
    }

    const isClockIn = statusData.status === "not_clocked_in";
    const confirmMessage = isClockIn
      ? "האם להחתים כניסה עכשיו?"
      : "האם להחתים יציאה עכשיו?";

    const confirmed = window.confirm(confirmMessage);

    if (!confirmed) {
      return;
    }

    const endpoint = isClockIn
      ? "/api/attendance/clock-in"
      : "/api/attendance/clock-out";

    const actionResponse = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: user.id }),
    });

    const actionData = await actionResponse.json();

    if (!actionResponse.ok) {
      alert(actionData.detail || "שגיאה בהחתמה");
      return;
    }

    alert(isClockIn ? "כניסה הוחתמה בהצלחה" : "יציאה הוחתמה בהצלחה");
  } catch (error) {
    console.error(error);
    alert("שגיאה בתקשורת עם השרת");
  }
}
  function closeActiveAction() {
    setActiveAction(null);
  }

  function handleAction(item) {
    if (item.key === "stickers" && user.role !== "admin") {
      alert("הפעולה מותרת למנהל המערכת בלבד");
      return;
    if (item.key === "timeClock") {
    handleTimeClockAction();
    return;
  }
    }

    const isInternalPage = Boolean(INTERNAL_COMPONENTS[item.key]);

    if (isInternalPage) {
      setActiveAction(item.key);
      return;
    }

    if (item.openInFrame) {
      setActiveAction(item.key);
      return;
    }

    if (item.url) {
      window.open(item.url, "_blank", "noopener,noreferrer");
      return;
    }

    alert("עדיין לא הוגדר קישור לפעולה הזאת");
  }

  return (
    <div className="portal">
      <div className="background-shape shape-1" />
      <div className="background-shape shape-2" />
      <div className="background-shape shape-3" />

      <header className="portal-header">
        <Logo className="header-logo" />

        <div className="header-user">
          <div>
            <div className="hello">שלום, {user.name} 👋</div>

            <div className="role-pill">{getRoleTitle(user.role)}</div>
          </div>
          {user.role === "warehouse" && (
            <EmployeeSwitcher currentUser={user} onSwitchUser={onSwitchUser} />
          )}

          <button
            type="button"
            className="chat-bell-button"
            onClick={() => setActiveAction("generalChat")}
            title="צ׳אט עובדים"
          >
            💬
            {unreadCount > 0 && (
              <span className="chat-bell-badge">{unreadCount}</span>
            )}
          </button>

          <button type="button" className="logout-top" onClick={onLogout}>
            יציאה
          </button>
        </div>
      </header>

      <main className="portal-main">
        <section className="hero">
          <div>
            <div className="hero-kicker">ADAR OPERATIONS</div>

            <h1>פורטל פעולות לעובדים</h1>

            <p>כל פעולות המחסן והמשרד במקום אחד</p>
          </div>
        </section>
       

        <section className="actions-section">
          <div className="section-title-row">
            <div>
              <h2>פעולות מהירות</h2>

              <p>בחר פעולה לפתיחה בתוך הפורטל</p>
            </div>
          </div>

          <div className="actions-grid">
            {menu.map((item) => (
              <ActionCard
                key={item.key}
                item={item}
                onClick={() => handleAction(item)}
              />
            ))}
          </div>
        </section>
      </main>

      {ActiveInternalComponent && (
        <ActiveInternalComponent onClose={closeActiveAction} user={user} />
      )}

      {activeMenuItem && !ActiveInternalComponent && activeMenuItem.openInFrame && (
        <FrameWindow
          title={activeMenuItem.title}
          url={activeMenuItem.url}
          onClose={closeActiveAction}
        />
      )}
    </div>
  );
}