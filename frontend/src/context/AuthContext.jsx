/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser, login as loginRequest, setUnauthorizedHandler } from "../services/api";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const [user, setUser] = useState(null); const [isLoading, setIsLoading] = useState(Boolean(token)); const [notice, setNotice] = useState("");
  const logout = (message = "") => { localStorage.removeItem("access_token"); setToken(null); setUser(null); setNotice(message); setIsLoading(false); };
  useEffect(() => { setUnauthorizedHandler(() => logout("Your session has expired. Please sign in again.")); return () => setUnauthorizedHandler(null); }, []);
  // Fetching an existing session is deliberately initiated when the stored token changes.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (!token) return; setIsLoading(true); getCurrentUser(token).then(setUser).catch(() => {}).finally(() => setIsLoading(false)); }, [token]);
  const login = async (email, password) => { const data = await loginRequest(email, password); localStorage.setItem("access_token", data.access_token); setNotice(""); setToken(data.access_token); const profile = await getCurrentUser(data.access_token); setUser(profile); return profile; };
  return <AuthContext.Provider value={{ token, user, isLoading, notice, login, logout, isAuthenticated: Boolean(token && user) }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error("useAuth must be used inside AuthProvider"); return context; }
