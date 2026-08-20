import { useState } from "react";
import Login from "./pages/Login";
import Portal from "./pages/Portal";

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("adarUser");
    return saved ? JSON.parse(saved) : null;
  });

  function login(userData) {
    setUser(userData);
    localStorage.setItem(
      "adarUser",
      JSON.stringify(userData)
    );
  }

  function logout() {
    localStorage.removeItem("adarUser");
    setUser(null);
  }

  return user ? (
    <ChatProvider user={user}>
      <Portal user={user} onLogout={logout} />
    </ChatProvider>
  ) : (
    <Login onLogin={login} />
  );
}