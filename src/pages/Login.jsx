import { useState } from "react";
import Logo from "../components/Logo";
export default function Login({ onLogin }) {
  const [username, setUsername] = useState("warehouse");
  const [password, setPassword] = useState("1234");
  return <div className="login-page"><div className="login-orb orb-blue"/><div className="login-orb orb-pink"/><div className="login-orb orb-yellow"/>
    <form className="login-card" onSubmit={(e)=>{e.preventDefault(); onLogin(username.trim(), password.trim());}}>
      <Logo className="login-logo-img"/><h1>פורטל עובדים</h1><p>מערכת פעולות ADAR Toys & More</p>
      <label>שם משתמש</label><input value={username} onChange={(e)=>setUsername(e.target.value)} />
      <label>סיסמה</label><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} />
      <button type="submit">כניסה למערכת</button>
      <div className="login-hint">בדיקה: warehouse / office / manager / admin<br/>סיסמה: 1234</div>
    </form></div>;
}
