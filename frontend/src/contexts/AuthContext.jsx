/**
 * RAMP Auth Context
 * =================
 * 
 * React Context for managing authentication state.
 * Provides user info, tokens, and auth operations.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Storage keys
const TOKEN_KEY = 'ramp_access_token';
const USER_KEY = 'ramp_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedUser = localStorage.getItem(USER_KEY);
    
    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        
        // Validate token is still valid
        const validateStoredToken = async () => {
          try {
            const res = await axios.get(`${API}/auth/me`, {
              headers: { Authorization: `Bearer ${storedToken}` }
            });
            setUser(res.data);
            localStorage.setItem(USER_KEY, JSON.stringify(res.data));
          } catch (e) {
            // Token invalid, clear auth
            clearAuth();
          }
        };
        validateStoredToken();
      } catch (e) {
        // Invalid stored data
        clearAuth();
      }
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Validate token with backend
  const validateToken = async (accessToken) => {
    try {
      const res = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      setUser(res.data);
      localStorage.setItem(USER_KEY, JSON.stringify(res.data));
    } catch (e) {
      // Token invalid, clear auth
      clearAuth();
    }
  };

  // Clear auth state
  const clearAuth = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };

  // Sign in
  const signIn = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await axios.post(`${API}/auth/signin`, { email, password });
      const { access_token, user: userData } = res.data;
      
      setToken(access_token);
      setUser(userData);
      
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
      
      setLoading(false);
      return { success: true };
    } catch (e) {
      const message = e.response?.data?.detail || 'Sign in failed';
      setError(message);
      setLoading(false);
      return { success: false, error: message };
    }
  }, []);

  // Sign up
  const signUp = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    
    try {
      const res = await axios.post(`${API}/auth/signup`, { email, password });
      const { access_token, user: userData } = res.data;
      
      setToken(access_token);
      setUser(userData);
      
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
      
      setLoading(false);
      return { success: true };
    } catch (e) {
      const message = e.response?.data?.detail || 'Sign up failed';
      setError(message);
      setLoading(false);
      return { success: false, error: message };
    }
  }, []);

  // Sign out
  const signOut = useCallback(() => {
    clearAuth();
    setError(null);
  }, []);

  // Check role access
  const canAccessHOW = user?.lens_access?.how || user?.role === 'admin' || user?.role === 'operator';
  const canAccessWHERE = user?.lens_access?.where || user?.role === 'admin' || user?.role === 'portfolio';
  const isAdmin = user?.role === 'admin';

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!token && !!user,
    canAccessHOW,
    canAccessWHERE,
    isAdmin,
    signIn,
    signUp,
    signOut,
    clearError: () => setError(null),
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
