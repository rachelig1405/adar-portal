import { useState } from "react";
import Logo from "../components/Logo";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "https://adar-portal-85ch.onrender.com";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/api/login`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: username.trim(),
            password: password.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
          "לא ניתן להתחבר למערכת"
        );
      }

      localStorage.setItem(
        "portal_user",
        JSON.stringify(data.user)
      );

      onLogin(data.user);
    } catch (error) {
      setError(
        error.message ||
        "אירעה שגיאה בהתחברות"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-orb orb-blue" />
      <div className="login-orb orb-pink" />
      <div className="login-orb orb-yellow" />

      <form
        className="login-card"
        onSubmit={handleSubmit}
      >
        <Logo className="login-logo-img" />

        <h1>פורטל עובדים</h1>

        <p>
          מערכת פעולות ADAR Toys & More
        </p>

        <label htmlFor="username">
          שם משתמש
        </label>

        <input
          id="username"
          value={username}
          onChange={(event) =>
            setUsername(event.target.value)
          }
          autoComplete="username"
          required
        />

        <label htmlFor="password">
          סיסמה
        </label>

        <input
          id="password"
          type="password"
          value={password}
          onChange={(event) =>
            setPassword(event.target.value)
          }
          autoComplete="current-password"
          required
        />

        {error && (
          <div className="login-error">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
        >
          {loading
            ? "מתחבר..."
            : "כניסה למערכת"}
        </button>
      </form>
    </div>
  );
}