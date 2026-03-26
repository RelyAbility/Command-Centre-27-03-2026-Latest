/**
 * RAMP WebSocket Store
 * ====================
 * 
 * Zustand store managing real-time application state via WebSockets.
 * Handles priority queue updates, state updates, and outcome updates.
 * 
 * Features:
 * - Authenticated WebSocket connections
 * - Automatic reconnection with exponential backoff
 * - Resync on reconnect
 * - Heartbeat handling
 * - Multi-channel support (priorities, states, outcomes)
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const WS_URL = BACKEND_URL?.replace(/^http/, 'ws');

// Reconnection settings
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const RECONNECT_MULTIPLIER = 2;
const HEARTBEAT_TIMEOUT = 45000; // Expect heartbeat every 30s, timeout at 45s

/**
 * Connection states
 */
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error',
};

/**
 * Create the RAMP store
 */
const useRAMPStore = create(
  subscribeWithSelector((set, get) => ({
    // =========================================================================
    // STATE
    // =========================================================================
    
    // Connection state
    connectionState: ConnectionState.DISCONNECTED,
    lastConnectedAt: null,
    lastError: null,
    reconnectAttempts: 0,
    
    // Auth token
    token: null,
    
    // Priorities channel
    priorities: [],
    prioritiesLastUpdate: null,
    
    // States channel (per asset)
    assetStates: {}, // { [assetId]: { states: [], lastUpdate: Date } }
    
    // Outcomes channel
    outcomes: [],
    outcomesLastUpdate: null,
    
    // Value summary (derived from outcomes)
    totalValueAtRisk: 0,
    totalValueRecoverable: 0,
    
    // Internal WebSocket references (not serialized)
    _ws: null,
    _reconnectTimer: null,
    _heartbeatTimer: null,
    _reconnectDelay: INITIAL_RECONNECT_DELAY,
    
    // =========================================================================
    // ACTIONS - CONNECTION
    // =========================================================================
    
    /**
     * Initialize the store with an auth token
     */
    setToken: (token) => {
      set({ token });
    },
    
    /**
     * Connect to the priorities WebSocket channel
     */
    connect: () => {
      const { token, _ws, connectionState } = get();
      
      if (!token) {
        console.warn('[RAMP WS] Cannot connect without token');
        set({ lastError: 'Authentication required' });
        return;
      }
      
      if (_ws && (connectionState === ConnectionState.CONNECTED || connectionState === ConnectionState.CONNECTING)) {
        console.log('[RAMP WS] Already connected or connecting');
        return;
      }
      
      // Clear any existing connection
      get().disconnect(false);
      
      set({ connectionState: ConnectionState.CONNECTING });
      
      try {
        const wsUrl = `${WS_URL}/api/ws/priorities?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('[RAMP WS] Connected to priorities channel');
          set({
            _ws: ws,
            connectionState: ConnectionState.CONNECTED,
            lastConnectedAt: new Date(),
            lastError: null,
            reconnectAttempts: 0,
            _reconnectDelay: INITIAL_RECONNECT_DELAY,
          });
          
          // Start heartbeat monitoring
          get()._startHeartbeatMonitor();
        };
        
        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            get()._handleMessage(message);
          } catch (e) {
            console.error('[RAMP WS] Failed to parse message:', e);
          }
        };
        
        ws.onerror = (error) => {
          console.error('[RAMP WS] WebSocket error:', error);
          set({ lastError: 'Connection error' });
        };
        
        ws.onclose = (event) => {
          console.log(`[RAMP WS] Disconnected (code: ${event.code}, reason: ${event.reason})`);
          get()._stopHeartbeatMonitor();
          
          // Handle authentication errors
          if (event.code === 4001) {
            set({
              connectionState: ConnectionState.ERROR,
              lastError: 'Authentication required',
              _ws: null,
            });
            return;
          }
          
          if (event.code === 4003) {
            set({
              connectionState: ConnectionState.ERROR,
              lastError: 'Access denied - HOW lens required',
              _ws: null,
            });
            return;
          }
          
          // Schedule reconnection for other disconnects
          set({ _ws: null });
          get()._scheduleReconnect();
        };
        
        set({ _ws: ws });
        
      } catch (error) {
        console.error('[RAMP WS] Failed to create WebSocket:', error);
        set({
          connectionState: ConnectionState.ERROR,
          lastError: error.message,
        });
      }
    },
    
    /**
     * Disconnect from WebSocket
     */
    disconnect: (clearState = true) => {
      const { _ws, _reconnectTimer, _heartbeatTimer } = get();
      
      // Clear timers
      if (_reconnectTimer) {
        clearTimeout(_reconnectTimer);
      }
      if (_heartbeatTimer) {
        clearTimeout(_heartbeatTimer);
      }
      
      // Close WebSocket
      if (_ws) {
        _ws.close(1000, 'Client disconnect');
      }
      
      const newState = {
        _ws: null,
        _reconnectTimer: null,
        _heartbeatTimer: null,
        connectionState: ConnectionState.DISCONNECTED,
      };
      
      if (clearState) {
        newState.priorities = [];
        newState.outcomes = [];
        newState.assetStates = {};
        newState.reconnectAttempts = 0;
        newState._reconnectDelay = INITIAL_RECONNECT_DELAY;
      }
      
      set(newState);
    },
    
    /**
     * Request a resync from the server
     */
    requestResync: () => {
      const { _ws, connectionState } = get();
      
      if (_ws && connectionState === ConnectionState.CONNECTED) {
        _ws.send(JSON.stringify({ type: 'resync_request' }));
      }
    },
    
    // =========================================================================
    // INTERNAL METHODS
    // =========================================================================
    
    /**
     * Handle incoming WebSocket messages
     */
    _handleMessage: (message) => {
      const { type, data, timestamp } = message;
      
      // Reset heartbeat timer on any message
      get()._resetHeartbeatTimer();
      
      switch (type) {
        case 'resync':
          get()._handleResync(data);
          break;
          
        case 'heartbeat':
          get()._handleHeartbeat(message);
          break;
          
        case 'priority_created':
        case 'priority_updated':
        case 'priority_escalated':
          get()._handlePriorityUpdate(data);
          break;
          
        case 'priority_expired':
          get()._handlePriorityExpired(data);
          break;
          
        case 'state_started':
        case 'state_ended':
        case 'state_transitioned':
          get()._handleStateUpdate(data);
          break;
          
        case 'outcome_verified':
          get()._handleOutcomeUpdate(data);
          break;
          
        case 'error':
          console.error('[RAMP WS] Server error:', message.message);
          set({ lastError: message.message });
          break;
          
        default:
          console.log('[RAMP WS] Unknown message type:', type, data);
      }
    },
    
    /**
     * Handle resync message (initial state on connect/reconnect)
     */
    _handleResync: (data) => {
      console.log('[RAMP WS] Raw resync data:', data);
      const { priorities = [], states = [], outcomes = [] } = data || {};
      
      console.log(`[RAMP WS] Resync received: ${priorities?.length || 0} priorities`);
      if (priorities && priorities.length > 0) {
        console.log('[RAMP WS] First priority:', priorities[0]);
      }
      
      // Calculate totals from priorities
      let totalVAR = 0;
      let totalVR = 0;
      
      priorities.forEach(p => {
        // Support both nested (economic_impact) and flat structures
        const varValue = p.value_at_risk_per_day || p.economic_impact?.value_at_risk_per_day || 0;
        const vrValue = p.value_recoverable_per_day || p.economic_impact?.value_recoverable_per_day || 0;
        totalVAR += varValue;
        totalVR += vrValue;
      });
      
      set({
        priorities,
        prioritiesLastUpdate: new Date(),
        totalValueAtRisk: totalVAR,
        totalValueRecoverable: totalVR,
      });
    },
    
    /**
     * Handle heartbeat from server
     */
    _handleHeartbeat: (message) => {
      const { _ws } = get();
      
      // Respond with pong
      if (_ws && _ws.readyState === WebSocket.OPEN) {
        _ws.send(JSON.stringify({ type: 'pong' }));
      }
    },
    
    /**
     * Handle priority update (create/update/escalate)
     */
    _handlePriorityUpdate: (data) => {
      const { priorities } = get();
      const priorityId = data.priority_id || data.id;
      
      // Find existing priority
      const existingIndex = priorities.findIndex(
        p => (p.priority_id || p.id) === priorityId
      );
      
      let newPriorities;
      
      if (existingIndex >= 0) {
        // Update existing
        newPriorities = [...priorities];
        newPriorities[existingIndex] = { ...newPriorities[existingIndex], ...data };
      } else {
        // Add new
        newPriorities = [...priorities, data];
      }
      
      // Re-sort by band (CRITICAL > HIGH > MEDIUM > LOW) then by score
      const bandOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      newPriorities.sort((a, b) => {
        const bandDiff = (bandOrder[a.priority_band] || 4) - (bandOrder[b.priority_band] || 4);
        if (bandDiff !== 0) return bandDiff;
        return (b.priority_score || 0) - (a.priority_score || 0);
      });
      
      // Recalculate totals
      let totalVAR = 0;
      let totalVR = 0;
      newPriorities.forEach(p => {
        const economic = p.economic_impact || {};
        totalVAR += economic.value_at_risk_per_day || 0;
        totalVR += economic.value_recoverable_per_day || 0;
      });
      
      set({
        priorities: newPriorities,
        prioritiesLastUpdate: new Date(),
        totalValueAtRisk: totalVAR,
        totalValueRecoverable: totalVR,
      });
    },
    
    /**
     * Handle priority expired
     */
    _handlePriorityExpired: (data) => {
      const { priorities } = get();
      const priorityId = data.priority_id || data.id;
      
      const newPriorities = priorities.filter(
        p => (p.priority_id || p.id) !== priorityId
      );
      
      // Recalculate totals
      let totalVAR = 0;
      let totalVR = 0;
      newPriorities.forEach(p => {
        const economic = p.economic_impact || {};
        totalVAR += economic.value_at_risk_per_day || 0;
        totalVR += economic.value_recoverable_per_day || 0;
      });
      
      set({
        priorities: newPriorities,
        prioritiesLastUpdate: new Date(),
        totalValueAtRisk: totalVAR,
        totalValueRecoverable: totalVR,
      });
    },
    
    /**
     * Handle state update
     */
    _handleStateUpdate: (data) => {
      const { assetStates } = get();
      const assetId = data.asset_id;
      
      if (!assetId) return;
      
      const current = assetStates[assetId] || { states: [], lastUpdate: null };
      let newStates;
      
      if (data.type === 'state_ended') {
        // Remove state
        newStates = current.states.filter(s => s.id !== data.state_id);
      } else {
        // Add/update state
        const existingIndex = current.states.findIndex(s => s.id === data.state_id);
        if (existingIndex >= 0) {
          newStates = [...current.states];
          newStates[existingIndex] = { ...newStates[existingIndex], ...data };
        } else {
          newStates = [...current.states, data];
        }
      }
      
      set({
        assetStates: {
          ...assetStates,
          [assetId]: {
            states: newStates,
            lastUpdate: new Date(),
          },
        },
      });
    },
    
    /**
     * Handle outcome update
     */
    _handleOutcomeUpdate: (data) => {
      const { outcomes } = get();
      
      set({
        outcomes: [...outcomes, data],
        outcomesLastUpdate: new Date(),
      });
    },
    
    /**
     * Schedule reconnection with exponential backoff
     */
    _scheduleReconnect: () => {
      const { _reconnectDelay, reconnectAttempts } = get();
      
      set({ connectionState: ConnectionState.RECONNECTING });
      
      console.log(`[RAMP WS] Reconnecting in ${_reconnectDelay}ms (attempt ${reconnectAttempts + 1})`);
      
      const timer = setTimeout(() => {
        set({
          reconnectAttempts: reconnectAttempts + 1,
          _reconnectDelay: Math.min(_reconnectDelay * RECONNECT_MULTIPLIER, MAX_RECONNECT_DELAY),
        });
        get().connect();
      }, _reconnectDelay);
      
      set({ _reconnectTimer: timer });
    },
    
    /**
     * Start heartbeat monitoring
     */
    _startHeartbeatMonitor: () => {
      get()._resetHeartbeatTimer();
    },
    
    /**
     * Reset heartbeat timer
     */
    _resetHeartbeatTimer: () => {
      const { _heartbeatTimer } = get();
      
      if (_heartbeatTimer) {
        clearTimeout(_heartbeatTimer);
      }
      
      const timer = setTimeout(() => {
        console.warn('[RAMP WS] Heartbeat timeout - reconnecting');
        const { _ws } = get();
        if (_ws) {
          _ws.close(4000, 'Heartbeat timeout');
        }
      }, HEARTBEAT_TIMEOUT);
      
      set({ _heartbeatTimer: timer });
    },
    
    /**
     * Stop heartbeat monitoring
     */
    _stopHeartbeatMonitor: () => {
      const { _heartbeatTimer } = get();
      if (_heartbeatTimer) {
        clearTimeout(_heartbeatTimer);
        set({ _heartbeatTimer: null });
      }
    },
    
    // =========================================================================
    // SELECTORS (Computed values)
    // =========================================================================
    
    /**
     * Get priorities by band
     */
    getPrioritiesByBand: (band) => {
      return get().priorities.filter(p => p.priority_band === band);
    },
    
    /**
     * Get priority distribution counts
     */
    getPriorityDistribution: () => {
      const { priorities } = get();
      return {
        CRITICAL: priorities.filter(p => p.priority_band === 'CRITICAL').length,
        HIGH: priorities.filter(p => p.priority_band === 'HIGH').length,
        MEDIUM: priorities.filter(p => p.priority_band === 'MEDIUM').length,
        LOW: priorities.filter(p => p.priority_band === 'LOW').length,
      };
    },
    
    /**
     * Get states for a specific asset
     */
    getAssetStates: (assetId) => {
      return get().assetStates[assetId]?.states || [];
    },
    
    /**
     * Check if connected
     */
    isConnected: () => {
      return get().connectionState === ConnectionState.CONNECTED;
    },
  }))
);

// Export connection states for use in components
export { ConnectionState };

export default useRAMPStore;
