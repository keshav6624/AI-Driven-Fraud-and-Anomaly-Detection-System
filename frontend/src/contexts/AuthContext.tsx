import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../api/client';

interface AuthState {
  token: string | null;
  role: string | null;
  username: string | null;
  login: (u: string, p: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthState>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem('role'));
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem('username'));

  const login = async (u: string, p: string) => {
    const res = await api.login(u, p);
    localStorage.setItem('token', res.access_token);
    localStorage.setItem('role', res.role);
    localStorage.setItem('username', res.username);
    setToken(res.access_token);
    setRole(res.role);
    setUsername(res.username);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    setToken(null);
    setRole(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ token, role, username, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
