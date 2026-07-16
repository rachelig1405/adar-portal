import { useMemo, useState } from "react";

import Logo from "../components/Logo";
import ActionCard from "../components/ActionCard";
import FrameWindow from "../components/FrameWindow";

import { getMenu } from "../data/menus";

import NewOrder from "./NewOrder";
import NewPicking from "./NewPicking";
import CheckOrder from "./CheckOrder";
import LoadingOrders from "./LoadOrder";
import EndPicking from "./EndPicking";

const INTERNAL_COMPONENTS = {
  newOrder: NewOrder,
  startPicking: NewPicking,
  endPicking: EndPicking,
  check: CheckOrder,
  loading:LoadingOrders
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


export default function Portal({ user, onLogout }) {
  const [activeAction, setActiveAction] = useState(null);

  const menu = useMemo(() => {
    return getMenu(user.role);
  }, [user.role]);

  const activeMenuItem = useMemo(() => {
    if (!activeAction) {
      return null;
    }

    return menu.find((item) => item.key === activeAction) || null;
  }, [activeAction, menu]);

  const ActiveInternalComponent =
    activeAction && INTERNAL_COMPONENTS[activeAction]
      ? INTERNAL_COMPONENTS[activeAction]
      : null;


  function closeActiveAction() {
    setActiveAction(null);
  }


  function handleAction(item) {
    const isInternalPage = Boolean(
      INTERNAL_COMPONENTS[item.key]
    );

    if (isInternalPage) {
      setActiveAction(item.key);
      return;
    }

    if (item.openInFrame) {
      setActiveAction(item.key);
      return;
    }

    if (item.url) {
      window.open(
        item.url,
        "_blank",
        "noopener,noreferrer"
      );
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
            <div className="hello">
              שלום, {user.name} 👋
            </div>

            <div className="role-pill">
              {getRoleTitle(user.role)}
            </div>
          </div>

          <button
            type="button"
            className="logout-top"
            onClick={onLogout}
          >
            יציאה
          </button>
        </div>
      </header>

      <main className="portal-main">
        <section className="hero">
          <div>
            <div className="hero-kicker">
              ADAR OPERATIONS
            </div>

            <h1>פורטל פעולות לעובדים</h1>

            <p>
              כל פעולות המחסן והמשרד במקום אחד
            </p>
          </div>
        </section>

        <section className="actions-section">
          <div className="section-title-row">
            <div>
              <h2>פעולות מהירות</h2>

              <p>
                בחרי פעולה לפתיחה בתוך הפורטל
              </p>
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
        <ActiveInternalComponent
          onClose={closeActiveAction}
        />
      )}

      {activeMenuItem &&
        !ActiveInternalComponent &&
        activeMenuItem.openInFrame && (
          <FrameWindow
            title={activeMenuItem.title}
            url={activeMenuItem.url}
            onClose={closeActiveAction}
          />
        )}
    </div>
  );
}


/*import { useMemo, useState } from "react";

import Logo from "../components/Logo";
import StatCard from "../components/StatCard";
import ActionCard from "../components/ActionCard";
import FrameWindow from "../components/FrameWindow";
import { getMenu } from "../data/menus";
import NewOrder from "./NewOrder"
import NewPicking from "./NewPicking";
const roleTitle = (role) => role === "warehouse" ? "מחסנאי" : role === "office" ? "משרד" : role === "manager" ? "מנהל מחסן" : "מנהל מערכת";

export default function Portal({ user, onLogout }) {
  const [active, setActive] = useState(null);
const [showNewOrder, setShowNewOrder] = useState(false);
  const menu = useMemo(() => getMenu(user.role), [user.role]);
  const selected = active ? menu.find((item) => item.key === active) : null;
  const [showNewPicking, setShowNewPicking] =
  useState(false);
  return <div className="portal">
    <div className="background-shape shape-1"/><div className="background-shape shape-2"/><div className="background-shape shape-3"/>
    <header className="portal-header"><Logo className="header-logo"/><div className="header-user"><div><div className="hello">שלום, {user.name} 👋</div><div className="role-pill">{roleTitle(user.role)}</div></div><button className="logout-top" onClick={onLogout}>יציאה</button></div></header>
    <main className="portal-main">
      <section className="hero"><div><div className="hero-kicker">ADAR OPERATIONS</div><h1>פורטל פעולות לעובדים</h1><p></p></div></section>
      <section className="actions-section"><div className="section-title-row"><div><h2>פעולות מהירות</h2><p>בחרי פעולה לפתיחה בתוך הפורטל</p></div></div>
      <div className="actions-grid">
  {menu.map((item) => (
    <ActionCard
      key={item.key}
      item={item}
      onClick={() => {
        if (item.key === "newOrder") {
          setShowNewOrder(true);
        } else {
          window.open(item.url, "_blank");
        }
      }}
    />
  ))}
</div></section>
    </main>
    {selected && (
  <FrameWindow
    title={selected.title}
    url={selected.url}
    onClose={() => setActive(null)}
  />
)}

{showNewOrder && (
  <NewOrder
    onClose={() => setShowNewOrder(false)}
  />
)}
  </div>;
}*/
   //  <section className="stats-grid"><StatCard icon="📦" number="143" label="הזמנות להיום" color="blue"/><StatCard icon="🟢" number="18" label="ממתינות לליקוט" color="green"/><StatCard icon="🚚" number="7" label="ממתינות להעמסה" color="pink"/><StatCard icon="⚡" number="96%" label="ביצוע יומי" color="yellow"/></section>
