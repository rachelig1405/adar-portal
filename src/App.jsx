import { useState } from "react";
import { USERS } from "./data/users";
import Login from "./pages/Login";
import Portal from "./pages/Portal";
export default function App() {
  const [user, setUser] = useState(() => { const saved = localStorage.getItem("adarUser"); return saved ? JSON.parse(saved) : null; });
  function login(username, password) { const found = USERS.find(u => u.username === username && u.password === password); if (!found) return alert("שם משתמש או סיסמה לא נכונים"); setUser(found); localStorage.setItem("adarUser", JSON.stringify(found)); }
  function logout() { localStorage.removeItem("adarUser"); setUser(null); }
  return user ? <Portal user={user} onLogout={logout}/> : <Login onLogin={login}/>;
}
