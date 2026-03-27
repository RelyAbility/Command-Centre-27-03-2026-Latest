/**
 * Industrial Intelligence Surface
 * ================================
 * 
 * Single-page unified dashboard for Rockwell demo.
 * Answers in <60 seconds:
 * 1. Where is value being lost? (VaR View)
 * 2. What should I do? (Action Layer)
 * 3. What has been recovered? (Verified Outcomes)
 * 4. Is the system working? (Trust Indicators)
 * 
 * "One screen that closes the deal"
 */

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useRAMPWebSocket } from '../hooks/useRAMPWebSocket';
import { ConnectionIndicator } from './ConnectionStatus';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Priority band colors
const BAND_COLORS = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-yellow-500 text-slate-900',
  LOW: 'bg-slate-500 text-white',
};

// Confidence colors
const CONFIDENCE_COLORS = {
  strong: 'text-emerald-400',
  moderate: 'text-yellow-400',
  low: 'text-orange-400',
  unknown: 'text-slate-400',
};

/**
 * Format currency
 */
const formatCurrency = (value, decimals = 0) => {
  if (value === null || value === undefined) return '$0';
  return `$${Number(value).toLocaleString(undefined, { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  })}`;
};

/**
 * Format time ago
 */
const timeAgo = (date) => {
  if (!date) return 'N/A';
  const now = new Date();
  const then = new Date(date);
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

/**
 * Main Industrial Intelligence Surface Component
 */
export function IntelligenceSurface() {
  const { token, user, signOut, canAccessHOW } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedPriority, setExpandedPriority] = useState(null);
  
  // WebSocket for real-time priority updates
  const { 
    priorities: wsPriorities,
    isConnected,
  } = useRAMPWebSocket(canAccessHOW ? token : null, { autoConnect: canAccessHOW });

  // Fetch aggregate metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      if (!token) return;
      
      try {
        const [summaryRes, outcomesRes, trustRes] = await Promise.all([
          axios.get(`${API}/intelligence/summary`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          axios.get(`${API}/intelligence/outcomes`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          axios.get(`${API}/intelligence/trust`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
        ]);
        
        setMetrics({
          summary: summaryRes.data,
          outcomes: outcomesRes.data,
          trust: trustRes.data,
        });
      } catch (e) {
        console.error('Failed to fetch metrics:', e);
        // Use fallback data for demo
        setMetrics({
          summary: { total_var: 0, total_recoverable: 0, priority_count: 0 },
          outcomes: { total_savings: 0, verified_count: 0, outcomes: [] },
          trust: { verification_rate: 0, actions_validated: 0, learning_improvement: 0 },
        });
      }
      setLoading(false);
    };
    
    fetchMetrics();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, [token]);

  // Calculate totals from WebSocket priorities
  const priorityMetrics = useMemo(() => {
    if (!wsPriorities || wsPriorities.length === 0) {
      return { totalVAR: 0, totalRecoverable: 0, count: 0, distribution: {} };
    }
    
    let totalVAR = 0;
    let totalRecoverable = 0;
    const distribution = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    
    wsPriorities.forEach(p => {
      const economic = p.economic_impact || {};
      totalVAR += p.value_at_risk_per_day || economic.value_at_risk_per_day || 0;
      totalRecoverable += p.value_recoverable_per_day || economic.value_recoverable_per_day || 0;
      distribution[p.priority_band] = (distribution[p.priority_band] || 0) + 1;
    });
    
    return { totalVAR, totalRecoverable, count: wsPriorities.length, distribution };
  }, [wsPriorities]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">Loading intelligence surface...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-lg font-semibold tracking-tight">
                RAMP <span className="text-slate-400 font-normal">Industrial Intelligence</span>
              </h1>
              <ConnectionIndicator />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-400">
                {user?.email}
              </span>
              <button
                onClick={signOut}
                className="text-sm text-slate-400 hover:text-white"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Single Page Surface */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        
        {/* ============================================ */}
        {/* SECTION 1: WHERE IS VALUE BEING LOST? (VaR) */}
        {/* ============================================ */}
        <section className="mb-6" data-testid="var-section">
          <div className="grid grid-cols-3 gap-4">
            {/* Total VAR */}
            <div className="bg-gradient-to-br from-red-900/30 to-slate-800 rounded-xl border border-red-800/30 p-5">
              <div className="text-xs text-red-400 uppercase tracking-wider mb-1">
                Value at Risk
              </div>
              <div className="text-4xl font-bold text-red-400" data-testid="total-var">
                {formatCurrency(priorityMetrics.totalVAR)}
                <span className="text-lg text-red-400/60">/day</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                {formatCurrency(priorityMetrics.totalVAR * 365)} annual exposure
              </div>
            </div>
            
            {/* Recoverable */}
            <div className="bg-gradient-to-br from-emerald-900/30 to-slate-800 rounded-xl border border-emerald-800/30 p-5">
              <div className="text-xs text-emerald-400 uppercase tracking-wider mb-1">
                Recoverable Value
              </div>
              <div className="text-4xl font-bold text-emerald-400" data-testid="total-recoverable">
                {formatCurrency(priorityMetrics.totalRecoverable)}
                <span className="text-lg text-emerald-400/60">/day</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                {((priorityMetrics.totalRecoverable / (priorityMetrics.totalVAR || 1)) * 100).toFixed(0)}% of VAR addressable
              </div>
            </div>
            
            {/* Priority Distribution */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                Active Priorities
              </div>
              <div className="text-4xl font-bold text-white mb-2">
                {priorityMetrics.count}
              </div>
              <div className="flex gap-2">
                {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(band => (
                  <div key={band} className="flex items-center gap-1">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[band]}`}>
                      {priorityMetrics.distribution[band] || 0}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Main Two-Column Layout */}
        <div className="grid grid-cols-5 gap-6">
          
          {/* ============================================ */}
          {/* SECTION 2: WHAT SHOULD I DO? (Actions)       */}
          {/* ============================================ */}
          <section className="col-span-3" data-testid="actions-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
                  Ranked Priorities
                </h2>
                <span className="text-xs text-emerald-400">
                  {isConnected ? 'Live' : 'Updating...'}
                </span>
              </div>
              
              <div className="divide-y divide-slate-700/50 max-h-[480px] overflow-y-auto">
                {wsPriorities?.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    No active priorities
                  </div>
                ) : (
                  wsPriorities?.map((priority, idx) => (
                    <PriorityCard
                      key={priority.priority_id || priority.id || idx}
                      priority={priority}
                      rank={idx + 1}
                      isExpanded={expandedPriority === (priority.priority_id || priority.id)}
                      onToggle={() => setExpandedPriority(
                        expandedPriority === (priority.priority_id || priority.id) 
                          ? null 
                          : (priority.priority_id || priority.id)
                      )}
                      token={token}
                    />
                  ))
                )}
              </div>
            </div>
          </section>

          {/* Right Column */}
          <div className="col-span-2 space-y-6">
            
            {/* ============================================ */}
            {/* SECTION 3: WHAT HAS BEEN RECOVERED?          */}
            {/* ============================================ */}
            <section data-testid="outcomes-section">
              <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-700">
                  <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
                    Verified Outcomes
                  </h2>
                </div>
                
                <div className="p-5">
                  {/* Total Verified Savings */}
                  <div className="mb-4">
                    <div className="text-xs text-slate-400 mb-1">Total Verified Savings</div>
                    <div className="text-3xl font-bold text-emerald-400" data-testid="total-savings">
                      {formatCurrency(metrics?.outcomes?.total_savings || 0)}
                    </div>
                    <div className="text-sm text-slate-500">
                      {metrics?.outcomes?.verified_count || 0} outcomes verified
                    </div>
                  </div>
                  
                  {/* Recent Outcomes */}
                  <div className="space-y-2">
                    {(metrics?.outcomes?.outcomes || []).slice(0, 3).map((outcome, idx) => (
                      <div key={idx} className="bg-slate-700/30 rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-white">{outcome.asset_name || 'Asset'}</span>
                          <span className="text-sm font-semibold text-emerald-400">
                            +{outcome.savings_value} {outcome.savings_unit}
                          </span>
                        </div>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-xs text-slate-500">
                            {timeAgo(outcome.verified_at)}
                          </span>
                          <span className={`text-xs capitalize ${CONFIDENCE_COLORS[outcome.confidence_band?.toLowerCase()] || CONFIDENCE_COLORS.unknown}`}>
                            {outcome.confidence_band || 'Unknown'} confidence
                          </span>
                        </div>
                      </div>
                    ))}
                    
                    {(!metrics?.outcomes?.outcomes || metrics.outcomes.outcomes.length === 0) && (
                      <div className="text-center py-4 text-slate-500 text-sm">
                        No verified outcomes yet
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* ============================================ */}
            {/* SECTION 4: IS THE SYSTEM WORKING? (Trust)    */}
            {/* ============================================ */}
            <section data-testid="trust-section">
              <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-700">
                  <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
                    System Trust
                  </h2>
                </div>
                
                <div className="p-5 space-y-4">
                  {/* Verification Rate */}
                  <TrustMetric
                    label="Verification Rate"
                    value={metrics?.trust?.verification_rate || 0}
                    format="percent"
                    description="Actions that reached verified outcome"
                  />
                  
                  {/* Actions Validated */}
                  <TrustMetric
                    label="Actions Validated"
                    value={metrics?.trust?.actions_validated || 0}
                    total={metrics?.trust?.total_actions || 0}
                    format="ratio"
                    description="Interventions with confirmed impact"
                  />
                  
                  {/* Learning Signal */}
                  <TrustMetric
                    label="Learning Active"
                    value={metrics?.trust?.learning_improvement || 0}
                    format="percent"
                    description="Outcomes improving baseline accuracy"
                    positive={true}
                  />
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800/80 backdrop-blur-sm border-t border-slate-700/50 px-6 py-2 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-500">
          <span>RAMP Industrial Intelligence</span>
          <ConnectionIndicator showLabel={true} />
        </div>
      </footer>
    </div>
  );
}

/**
 * Priority Card with Expandable Traceability
 */
function PriorityCard({ priority, rank, isExpanded, onToggle, token }) {
  const [traceData, setTraceData] = useState(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  
  const economic = priority.economic_impact || {};
  const var_value = priority.value_at_risk_per_day || economic.value_at_risk_per_day || 0;
  const confidence = priority.confidence_label || 'unknown';
  
  // Fetch trace data when expanded
  useEffect(() => {
    if (isExpanded && !traceData && !loadingTrace) {
      setLoadingTrace(true);
      axios.get(`${API}/intelligence/trace/${priority.state_id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => setTraceData(res.data))
        .catch(() => setTraceData({ state: priority, intervention: null, outcome: null }))
        .finally(() => setLoadingTrace(false));
    }
  }, [isExpanded, traceData, loadingTrace, priority, token]);

  return (
    <div 
      className="px-5 py-4 hover:bg-slate-700/20 cursor-pointer transition-colors"
      onClick={onToggle}
      data-testid={`priority-card-${rank}`}
    >
      {/* Main Row */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-slate-600 w-8">#{rank}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[priority.priority_band]}`}>
                {priority.priority_band}
              </span>
              <span className="font-medium text-white">
                {priority.asset_name || priority.asset_id}
              </span>
            </div>
            <div className="text-sm text-slate-400 mt-0.5">
              {priority.drivers?.[0] || priority.state_type || 'Active condition'}
            </div>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-lg font-semibold text-amber-400">
            {formatCurrency(var_value)}<span className="text-xs text-slate-400">/day</span>
          </div>
          <div className={`text-xs capitalize ${CONFIDENCE_COLORS[confidence.toLowerCase()] || CONFIDENCE_COLORS.unknown}`}>
            {confidence} confidence
          </div>
        </div>
      </div>
      
      {/* Expandable Traceability Chain */}
      {isExpanded && (
        <div className="mt-4 ml-11 border-l-2 border-slate-600 pl-4 space-y-3" data-testid="trace-chain">
          {loadingTrace ? (
            <div className="text-slate-500 text-sm">Loading trace...</div>
          ) : (
            <>
              {/* State Detected */}
              <TraceStep
                icon="🔍"
                label="State Detected"
                time={traceData?.state?.started_at || priority.created_at}
                detail={`${priority.state_type || 'Condition'} identified`}
                status="complete"
              />
              
              {/* Priority Created */}
              <TraceStep
                icon="⚡"
                label="Priority Created"
                time={priority.created_at}
                detail={`${priority.priority_band} - Score ${priority.priority_score || 0}`}
                status="complete"
              />
              
              {/* Intervention */}
              <TraceStep
                icon="🔧"
                label="Intervention"
                time={traceData?.intervention?.created_at}
                detail={traceData?.intervention 
                  ? `${traceData.intervention.intervention_type} by ${traceData.intervention.created_by}`
                  : 'Awaiting action'
                }
                status={traceData?.intervention ? 'complete' : 'pending'}
              />
              
              {/* Outcome */}
              <TraceStep
                icon="✓"
                label="Outcome Verified"
                time={traceData?.outcome?.verified_at}
                detail={traceData?.outcome 
                  ? `${traceData.outcome.savings_value} ${traceData.outcome.savings_unit} saved`
                  : 'Pending verification'
                }
                status={traceData?.outcome ? 'complete' : 'pending'}
              />
            </>
          )}
        </div>
      )}
      
      {/* Expand indicator */}
      <div className="mt-2 ml-11 text-xs text-slate-500">
        {isExpanded ? '▲ Collapse' : '▼ View trace'}
      </div>
    </div>
  );
}

/**
 * Trace Step Component
 */
function TraceStep({ icon, label, time, detail, status }) {
  const isComplete = status === 'complete';
  
  return (
    <div className={`flex items-start gap-3 ${!isComplete ? 'opacity-50' : ''}`}>
      <span className="text-lg">{icon}</span>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${isComplete ? 'text-white' : 'text-slate-400'}`}>
            {label}
          </span>
          {time && (
            <span className="text-xs text-slate-500">{timeAgo(time)}</span>
          )}
        </div>
        <div className="text-xs text-slate-400">{detail}</div>
      </div>
    </div>
  );
}

/**
 * Trust Metric Component
 */
function TrustMetric({ label, value, total, format, description, positive }) {
  let displayValue;
  
  if (format === 'percent') {
    displayValue = `${(value * 100).toFixed(0)}%`;
  } else if (format === 'ratio' && total !== undefined) {
    displayValue = `${value}/${total}`;
  } else {
    displayValue = value;
  }
  
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-300">{label}</span>
        <span className={`text-lg font-semibold ${positive ? 'text-emerald-400' : 'text-white'}`}>
          {displayValue}
        </span>
      </div>
      {format === 'percent' && (
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full ${positive ? 'bg-emerald-500' : 'bg-slate-400'}`}
            style={{ width: `${Math.min(value * 100, 100)}%` }}
          />
        </div>
      )}
      <div className="text-xs text-slate-500 mt-1">{description}</div>
    </div>
  );
}

export default IntelligenceSurface;
