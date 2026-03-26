/**
 * RAMP Connection Status Indicator
 * =================================
 * 
 * Visual indicator for WebSocket connection status.
 * Shows connected, connecting, reconnecting, or error states.
 */

import React from 'react';
import { useRAMPConnectionStatus } from '../hooks/useRAMPWebSocket';
import { ConnectionState } from '../stores/useRAMPStore';

const STATUS_CONFIG = {
  [ConnectionState.CONNECTED]: {
    label: 'Live',
    color: 'bg-emerald-500',
    textColor: 'text-emerald-400',
    pulse: true,
  },
  [ConnectionState.CONNECTING]: {
    label: 'Connecting',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-400',
    pulse: true,
  },
  [ConnectionState.RECONNECTING]: {
    label: 'Reconnecting',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-400',
    pulse: true,
  },
  [ConnectionState.DISCONNECTED]: {
    label: 'Offline',
    color: 'bg-slate-500',
    textColor: 'text-slate-400',
    pulse: false,
  },
  [ConnectionState.ERROR]: {
    label: 'Error',
    color: 'bg-red-500',
    textColor: 'text-red-400',
    pulse: false,
  },
};

/**
 * Compact connection indicator (dot + label)
 */
export function ConnectionIndicator({ 
  showLabel = true, 
  className = '' 
}) {
  const { connectionState, reconnectAttempts } = useRAMPConnectionStatus();
  
  const config = STATUS_CONFIG[connectionState] || STATUS_CONFIG[ConnectionState.DISCONNECTED];
  
  return (
    <div 
      className={`flex items-center gap-2 ${className}`}
      data-testid="connection-indicator"
    >
      <div 
        className={`w-2 h-2 rounded-full ${config.color} ${config.pulse ? 'animate-pulse' : ''}`}
      />
      {showLabel && (
        <span className={`text-xs font-medium ${config.textColor}`}>
          {config.label}
          {connectionState === ConnectionState.RECONNECTING && reconnectAttempts > 0 && (
            <span className="text-slate-500 ml-1">
              (attempt {reconnectAttempts})
            </span>
          )}
        </span>
      )}
    </div>
  );
}

/**
 * Detailed connection status card
 */
export function ConnectionStatusCard({ 
  onRetry, 
  className = '' 
}) {
  const { 
    connectionState, 
    lastError, 
    reconnectAttempts,
    isConnected,
    hasError 
  } = useRAMPConnectionStatus();
  
  const config = STATUS_CONFIG[connectionState] || STATUS_CONFIG[ConnectionState.DISCONNECTED];
  
  if (isConnected) {
    return null; // Don't show card when connected
  }
  
  return (
    <div 
      className={`bg-slate-800 border border-slate-700 rounded-lg p-4 ${className}`}
      data-testid="connection-status-card"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div 
            className={`w-3 h-3 rounded-full ${config.color} ${config.pulse ? 'animate-pulse' : ''}`}
          />
          <div>
            <div className={`font-medium ${config.textColor}`}>
              {config.label}
            </div>
            {lastError && (
              <div className="text-sm text-slate-400 mt-0.5">
                {lastError}
              </div>
            )}
            {connectionState === ConnectionState.RECONNECTING && (
              <div className="text-sm text-slate-500 mt-0.5">
                Attempt {reconnectAttempts} - Reconnecting automatically...
              </div>
            )}
          </div>
        </div>
        
        {(hasError || connectionState === ConnectionState.DISCONNECTED) && onRetry && (
          <button
            onClick={onRetry}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-slate-300 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Inline reconnecting banner
 */
export function ReconnectingBanner({ className = '' }) {
  const { connectionState, reconnectAttempts } = useRAMPConnectionStatus();
  
  if (connectionState !== ConnectionState.RECONNECTING) {
    return null;
  }
  
  return (
    <div 
      className={`bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-4 py-2 flex items-center gap-3 ${className}`}
      data-testid="reconnecting-banner"
    >
      <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
      <span className="text-sm text-yellow-400">
        Reconnecting to live updates (attempt {reconnectAttempts})...
      </span>
    </div>
  );
}

export default ConnectionIndicator;
