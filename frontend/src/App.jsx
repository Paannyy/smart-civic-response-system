import { useState } from "react";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState("login");
  if (isLoading) return <main className="app-loading"><span className="spinner" /> Restoring your session…</main>;
  if (isAuthenticated) return <Dashboard />;
  return authView === "signup" ? <Signup onLogin={() => setAuthView("login")} /> : <Login onSignup={() => setAuthView("signup")} />;
}
