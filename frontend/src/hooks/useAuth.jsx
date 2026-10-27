import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError } from "../services/api";

const AuthContext = createContext(null);

/**
 * Knows who is logged in. On start-up it asks Django for a CSRF cookie and
 * then for the current user (403 simply means "not logged in").
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  const check = useCallback(async () => {
    setStatus("loading");
    try {
      await api.csrf();
      const { user } = await api.me();
      setUser(user);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setUser(null);
      } else {
        setError(err);
        setStatus("error");
        return;
      }
    }
    setStatus("ready");
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  const login = async (email, password) => setUser((await api.login(email, password)).user);
  const register = async (name, email, password) => setUser((await api.register(name, email, password)).user);
  const logout = async () => {
    await api.logout();
    setUser(null);
    await api.csrf(); // fresh token for the next login
  };

  return (
    <AuthContext.Provider value={{ user, status, error, retry: check, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
