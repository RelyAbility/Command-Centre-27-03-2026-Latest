/**
 * RAMP Login Component
 * ====================
 * 
 * Simple login form for authentication.
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

export function LoginForm({ onSuccess, initialEmail = '', initialPassword = '' }) {
  const { signIn, loading, error, clearError } = useAuth();
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState(initialPassword);

  // Update from props
  useEffect(() => {
    if (initialEmail) setEmail(initialEmail);
    if (initialPassword) setPassword(initialPassword);
  }, [initialEmail, initialPassword]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    
    const result = await signIn(email, password);
    if (result.success && onSuccess) {
      onSuccess();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm text-slate-400 mb-1.5">
          Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2.5 focus:border-emerald-500 outline-none text-white"
          placeholder="your@email.com"
          required
          disabled={loading}
          data-testid="login-email"
        />
      </div>
      
      <div>
        <label className="block text-sm text-slate-400 mb-1.5">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2.5 focus:border-emerald-500 outline-none text-white"
          placeholder="••••••••"
          required
          disabled={loading}
          data-testid="login-password"
        />
      </div>
      
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-sm text-red-400">
          {error}
        </div>
      )}
      
      <button
        type="submit"
        disabled={loading}
        className="w-full px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors disabled:opacity-50"
        data-testid="login-submit"
      >
        {loading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  );
}

/**
 * Demo credentials helper
 */
export function DemoCredentials({ onSelect }) {
  const credentials = [
    { 
      role: 'Operator', 
      email: 'operator1@gmail.com', 
      password: 'Operator2024!',
      description: 'HOW lens access - operational view'
    },
    { 
      role: 'Portfolio', 
      email: 'portfolio1@gmail.com', 
      password: 'Portfolio2024!',
      description: 'WHERE lens access - aggregated view'
    },
    { 
      role: 'Admin', 
      email: 'rampadmin@gmail.com', 
      password: 'RampAdmin2024!',
      description: 'Full access - both lenses'
    },
  ];

  return (
    <div className="space-y-2">
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">
        Demo Accounts
      </div>
      {credentials.map((cred) => (
        <button
          key={cred.role}
          onClick={() => onSelect(cred.email, cred.password)}
          className="w-full text-left px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-colors group"
          data-testid={`demo-${cred.role.toLowerCase()}`}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-300 group-hover:text-white">
              {cred.role}
            </span>
            <span className="text-xs text-slate-500">
              {cred.email}
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            {cred.description}
          </div>
        </button>
      ))}
    </div>
  );
}

export default LoginForm;
