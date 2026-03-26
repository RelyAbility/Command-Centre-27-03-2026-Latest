/**
 * useRAMPWebSocket Hook
 * =====================
 * 
 * React hook for managing RAMP WebSocket connections.
 * Provides easy integration with the Zustand store and auth context.
 * 
 * Features:
 * - Auto-connect when token is available
 * - Auto-disconnect on unmount
 * - Connection status indicators
 * - Typed selectors for priorities, states, outcomes
 * 
 * Usage:
 * ```jsx
 * const { 
 *   priorities,
 *   isConnected,
 *   connectionState,
 *   connect,
 *   disconnect 
 * } = useRAMPWebSocket(authToken);
 * ```
 */

import { useEffect, useCallback, useMemo } from 'react';
import useRAMPStore, { ConnectionState } from '../stores/useRAMPStore';

/**
 * Main WebSocket hook for RAMP real-time updates
 * 
 * @param {string|null} token - JWT auth token
 * @param {Object} options - Hook options
 * @param {boolean} options.autoConnect - Auto-connect when token available (default: true)
 * @param {boolean} options.autoDisconnect - Disconnect on unmount (default: true)
 */
export function useRAMPWebSocket(token, options = {}) {
  const { 
    autoConnect = true, 
    autoDisconnect = true 
  } = options;
  
  // Store actions
  const setToken = useRAMPStore(state => state.setToken);
  const connect = useRAMPStore(state => state.connect);
  const disconnect = useRAMPStore(state => state.disconnect);
  const requestResync = useRAMPStore(state => state.requestResync);
  
  // Store state
  const connectionState = useRAMPStore(state => state.connectionState);
  const lastError = useRAMPStore(state => state.lastError);
  const reconnectAttempts = useRAMPStore(state => state.reconnectAttempts);
  const lastConnectedAt = useRAMPStore(state => state.lastConnectedAt);
  
  // Priority data
  const priorities = useRAMPStore(state => state.priorities);
  const prioritiesLastUpdate = useRAMPStore(state => state.prioritiesLastUpdate);
  const totalValueAtRisk = useRAMPStore(state => state.totalValueAtRisk);
  const totalValueRecoverable = useRAMPStore(state => state.totalValueRecoverable);
  
  // Outcomes
  const outcomes = useRAMPStore(state => state.outcomes);
  const outcomesLastUpdate = useRAMPStore(state => state.outcomesLastUpdate);
  
  // Selectors
  const getPriorityDistribution = useRAMPStore(state => state.getPriorityDistribution);
  const getPrioritiesByBand = useRAMPStore(state => state.getPrioritiesByBand);
  const getAssetStates = useRAMPStore(state => state.getAssetStates);
  
  // Derived state
  const isConnected = connectionState === ConnectionState.CONNECTED;
  const isConnecting = connectionState === ConnectionState.CONNECTING;
  const isReconnecting = connectionState === ConnectionState.RECONNECTING;
  const hasError = connectionState === ConnectionState.ERROR;
  
  // Priority distribution (memoized)
  const priorityDistribution = useMemo(() => {
    return {
      CRITICAL: priorities.filter(p => p.priority_band === 'CRITICAL').length,
      HIGH: priorities.filter(p => p.priority_band === 'HIGH').length,
      MEDIUM: priorities.filter(p => p.priority_band === 'MEDIUM').length,
      LOW: priorities.filter(p => p.priority_band === 'LOW').length,
    };
  }, [priorities]);
  
  // Set token when it changes
  useEffect(() => {
    if (token) {
      setToken(token);
    }
  }, [token, setToken]);
  
  // Auto-connect when token is available
  useEffect(() => {
    if (autoConnect && token && connectionState === ConnectionState.DISCONNECTED) {
      connect();
    }
  }, [autoConnect, token, connectionState, connect]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (autoDisconnect) {
        disconnect(false); // Don't clear state on unmount, just disconnect
      }
    };
  }, [autoDisconnect, disconnect]);
  
  // Manual connect function (resets reconnect state)
  const manualConnect = useCallback(() => {
    if (token) {
      connect();
    } else {
      console.warn('[useRAMPWebSocket] Cannot connect without token');
    }
  }, [token, connect]);
  
  // Manual disconnect function
  const manualDisconnect = useCallback(() => {
    disconnect(true);
  }, [disconnect]);
  
  return {
    // Connection state
    connectionState,
    isConnected,
    isConnecting,
    isReconnecting,
    hasError,
    lastError,
    reconnectAttempts,
    lastConnectedAt,
    
    // Priority data
    priorities,
    priorityDistribution,
    prioritiesLastUpdate,
    totalValueAtRisk,
    totalValueRecoverable,
    
    // Outcomes
    outcomes,
    outcomesLastUpdate,
    
    // Actions
    connect: manualConnect,
    disconnect: manualDisconnect,
    requestResync,
    
    // Selectors
    getPrioritiesByBand,
    getAssetStates,
  };
}

/**
 * Lightweight hook for just connection status
 * Use when you only need to show connection indicator
 */
export function useRAMPConnectionStatus() {
  const connectionState = useRAMPStore(state => state.connectionState);
  const lastError = useRAMPStore(state => state.lastError);
  const reconnectAttempts = useRAMPStore(state => state.reconnectAttempts);
  
  return {
    connectionState,
    isConnected: connectionState === ConnectionState.CONNECTED,
    isConnecting: connectionState === ConnectionState.CONNECTING,
    isReconnecting: connectionState === ConnectionState.RECONNECTING,
    hasError: connectionState === ConnectionState.ERROR,
    lastError,
    reconnectAttempts,
  };
}

/**
 * Hook for priority queue updates only
 * Use when you only need priority data
 */
export function useRAMPPriorities() {
  const priorities = useRAMPStore(state => state.priorities);
  const lastUpdate = useRAMPStore(state => state.prioritiesLastUpdate);
  const totalValueAtRisk = useRAMPStore(state => state.totalValueAtRisk);
  const totalValueRecoverable = useRAMPStore(state => state.totalValueRecoverable);
  
  const distribution = useMemo(() => ({
    CRITICAL: priorities.filter(p => p.priority_band === 'CRITICAL').length,
    HIGH: priorities.filter(p => p.priority_band === 'HIGH').length,
    MEDIUM: priorities.filter(p => p.priority_band === 'MEDIUM').length,
    LOW: priorities.filter(p => p.priority_band === 'LOW').length,
    total: priorities.length,
  }), [priorities]);
  
  return {
    priorities,
    distribution,
    lastUpdate,
    totalValueAtRisk,
    totalValueRecoverable,
  };
}

/**
 * Hook for specific asset states
 * Use when monitoring a single asset's state
 */
export function useRAMPAssetStates(assetId) {
  const assetStates = useRAMPStore(state => state.assetStates);
  
  return {
    states: assetStates[assetId]?.states || [],
    lastUpdate: assetStates[assetId]?.lastUpdate || null,
    hasActiveStates: (assetStates[assetId]?.states || []).length > 0,
  };
}

/**
 * Hook for outcome notifications
 */
export function useRAMPOutcomes() {
  const outcomes = useRAMPStore(state => state.outcomes);
  const lastUpdate = useRAMPStore(state => state.outcomesLastUpdate);
  
  // Get recent outcomes (last 10)
  const recentOutcomes = useMemo(() => {
    return outcomes.slice(-10).reverse();
  }, [outcomes]);
  
  return {
    outcomes,
    recentOutcomes,
    lastUpdate,
    count: outcomes.length,
  };
}

export default useRAMPWebSocket;
