import { useState } from "react";
import { register } from "../services/api";

export default function Signup({ onLogin }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const change = (event) => {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      await register(form.name, form.email, form.password);
      setSuccess("Your account has been created. Please sign in.");
      window.setTimeout(onLogin, 1000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-intro">
        <p className="eyebrow">SMART CIVIC RESPONSE</p>
        <h1>Your neighbourhood, heard and improved.</h1>
        <p>Create a citizen account to submit civic issues and follow every update.</p>
      </section>

      <section className="login-card">
        <div>
          <p className="eyebrow">CREATE ACCOUNT</p>
          <h2>Join the civic portal</h2>
          <p className="muted">Accounts are created as citizen accounts.</p>
        </div>

        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
        {success && (
          <p className="notice" role="status">
            {success}
          </p>
        )}

        <form onSubmit={submit}>
          <label>
            Full name
            <input
              name="name"
              value={form.name}
              onChange={change}
              minLength="2"
              maxLength="100"
              autoComplete="name"
              required
            />
          </label>

          <label>
            Email address
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={change}
              autoComplete="email"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={change}
              minLength="8"
              maxLength="128"
              autoComplete="new-password"
              required
            />
          </label>

          <button className="primary" disabled={loading || Boolean(success)}>
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="muted">
          Already have an account?{" "}
          <button type="button" className="text-button" onClick={onLogin}>
            Sign in
          </button>
        </p>
      </section>
    </main>
  );
}
