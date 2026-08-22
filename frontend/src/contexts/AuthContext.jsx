import React, { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const decoded = jwtDecode(token);
          // Allow token decode even if close to expiry, the interceptor handles refresh
          setUser({
            id: decoded.sub || decoded.id,
            role: decoded.role || 'user',
            email: decoded.email || decoded.sub
          });
        } catch (e) {
          console.error("Failed to decode token", e);
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = (access_token, refresh_token) => {
    localStorage.setItem('token', access_token);
    if (refresh_token) {
      localStorage.setItem('refresh_token', refresh_token);
    }
    try {
      const decoded = jwtDecode(access_token);
      setUser({
        id: decoded.sub || decoded.id,
        role: decoded.role || 'user',
        email: decoded.email || decoded.sub
      });
    } catch (e) {
      console.error("Failed to decode token on login", e);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
