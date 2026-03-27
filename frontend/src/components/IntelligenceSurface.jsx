/**
 * Industrial Intelligence Surface
 * ================================
 * 
 * Single-page unified dashboard for Rockwell demo.
 * Supports TWO modes from the SAME surface:
 * 
 * OPERATOR MODE (HOW lens):
 *   Asset/system level, action-focused
 *   WebSocket real-time priorities
 * 
 * PORTFOLIO MODE (WHERE lens):
 *   Site-level aggregation
 *   Focus = "where to act"
 *   Ranked sites by VaR
 * 
 * Answers in <60 seconds:
 * 1. Where is value being lost? (VaR View)
 * 2. What should I do? (Action Layer / Site Focus)
 * 3. What has been recovered? (Verified Outcomes)
 * 4. Is the system working? (Trust Indicators)
 */

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useRAMPWebSocket } from '../hooks/useRAMPWebSocket';
import { ConnectionIndicator } from './ConnectionStatus';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const BAND_COLORS = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-yellow-500 text-slate-900',
  LOW: 'bg-slate-500 text-white',
};

const CONFIDENCE_COLORS = {
  strong: 'text-emerald-400',
  moderate: 'text-yellow-400',
  low: 'text-orange-400',
  unknown: 'text-slate-400',
};

const formatCurrency = (value, decimals = 0) => {
  if (value === null || value === undefined) return '$0';
  return `$${Number(value).toLocaleString(undefined, { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  })}`;
};

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

export function IntelligenceSurface() {
  const { token, user, signOut, canAccessHOW, canAccessWHERE } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedPriority, setExpandedPriority] = useState(null);
  
  // Determine mode: portfolio users who can't access HOW get portfolio mode
  const isPortfolioMode = canAccessWHERE && !canAccessHOW;
  
  // WebSocket for operator mode only
  const { 
    priorities: wsPriorities,
    isConnected,
  } = useRAMPWebSocket(
    canAccessHOW ? token : null, 
    { autoConnect: canAccessHOW }
  );

  // Fetch data based on mode
  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      
      try {
        if (isPortfolioMode) {
          // Portfolio mode: single endpoint returns everything
          const res = await axios.get(`${API}/where/portfolio/intelligence`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setPortfolioData(res.data);
        } else {
          // Operator mode: fetch from intelligence endpoints
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
        }
      } catch (e) {
        console.error('Failed to fetch intelligence data:', e);
        if (isPortfolioMode) {
          setPortfolioData({ summary: { total_var: 0, total_recoverable: 0, site_count: 0, priority_count: 0 }, sites: [], outcomes: { total_savings: 0, verified_count: 0, site_outcomes: [] }, trust: { verification_rate: 0, actions_validated: 0, learning_improvement: 0 }, focus_site: null });
        } else {
          setMetrics({
            summary: { total_var: 0, total_recoverable: 0, priority_count: 0 },
            outcomes: { total_savings: 0, verified_count: 0, outcomes: [] },
            trust: { verification_rate: 0, actions_validated: 0, learning_improvement: 0 },
          });
        }
      }
      setLoading(false);
    };
    
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [token, isPortfolioMode]);

  // Calculate totals from WebSocket priorities (operator mode)
  const priorityMetrics = useMemo(() => {
    if (isPortfolioMode || !wsPriorities || wsPriorities.length === 0) {
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
  }, [wsPriorities, isPortfolioMode]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400" data-testid="loading-indicator">Loading intelligence surface...</div>
      </div>
    );
  }

  // Resolve VaR values for the top section
  const varTotal = isPortfolioMode 
    ? portfolioData?.summary?.total_var || 0 
    : priorityMetrics.totalVAR;
  const recoverableTotal = isPortfolioMode 
    ? portfolioData?.summary?.total_recoverable || 0 
    : priorityMetrics.totalRecoverable;
  const itemCount = isPortfolioMode 
    ? portfolioData?.summary?.site_count || 0 
    : priorityMetrics.count;
  const totalDistribution = isPortfolioMode 
    ? (portfolioData?.sites || []).reduce((acc, s) => {
        Object.entries(s.distribution || {}).forEach(([band, count]) => {
          acc[band] = (acc[band] || 0) + count;
        });
        return acc;
      }, { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 })
    : priorityMetrics.distribution;

  // Outcomes
  const outcomesData = isPortfolioMode ? portfolioData?.outcomes : metrics?.outcomes;
  const trustData = isPortfolioMode ? portfolioData?.trust : metrics?.trust;

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
              {isPortfolioMode ? (
                <span className="text-xs px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300" data-testid="mode-badge">
                  Portfolio
                </span>
              ) : (
                <ConnectionIndicator />
              )}
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-400" data-testid="user-email">
                {user?.email}
              </span>
              <button
                onClick={signOut}
                className="text-sm text-slate-400 hover:text-white"
                data-testid="sign-out-btn"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        
        {/* ============================================ */}
        {/* FOCUS SITE CALLOUT (Portfolio mode only)     */}
        {/* ============================================ */}
        {isPortfolioMode && portfolioData?.focus_site && (
          <section className="mb-6" data-testid="focus-site-callout">
            <div className="bg-gradient-to-r from-amber-900/40 via-amber-900/20 to-slate-800 rounded-xl border border-amber-600/30 p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs text-amber-400 uppercase tracking-wider font-medium mb-0.5">
                    Focus here first
                  </div>
                  <div className="text-lg font-semibold text-white" data-testid="focus-site-name">
                    {portfolioData.focus_site.site_name}
                  </div>
                  <div className="text-sm text-slate-400">
                    {portfolioData.focus_site.reason}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-amber-400" data-testid="focus-site-var">
                  {formatCurrency(portfolioData.focus_site.var_per_day)}
                  <span className="text-sm text-amber-400/60">/day</span>
                </div>
                <div className="text-xs text-slate-400">value at risk</div>
              </div>
            </div>
          </section>
        )}

        {/* ============================================ */}
        {/* SECTION 1: WHERE IS VALUE BEING LOST? (VaR) */}
        {/* ============================================ */}
        <section className="mb-6" data-testid="var-section">
          <div className="grid grid-cols-3 gap-4">
            {/* Total VAR */}
            <div className="bg-gradient-to-br from-red-900/30 to-slate-800 rounded-xl border border-red-800/30 p-5">
              <div className="text-xs text-red-400 uppercase tracking-wider mb-1">
                {isPortfolioMode ? 'Portfolio Value at Risk' : 'Value at Risk'}
              </div>
              <div className="text-4xl font-bold text-red-400" data-testid="total-var">
                {formatCurrency(varTotal)}
                <span className="text-lg text-red-400/60">/day</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                {formatCurrency(varTotal * 365)} annual exposure
              </div>
            </div>
            
            {/* Recoverable */}
            <div className="bg-gradient-to-br from-emerald-900/30 to-slate-800 rounded-xl border border-emerald-800/30 p-5">
              <div className="text-xs text-emerald-400 uppercase tracking-wider mb-1">
                Recoverable Value
              </div>
              <div className="text-4xl font-bold text-emerald-400" data-testid="total-recoverable">
                {formatCurrency(recoverableTotal)}
                <span className="text-lg text-emerald-400/60">/day</span>
              </div>
              <div className="text-sm text-slate-400 mt-1">
                {((recoverableTotal / (varTotal || 1)) * 100).toFixed(0)}% of VAR addressable
              </div>
            </div>
            
            {/* Count — Sites or Priorities depending on mode */}
            <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-2">
                {isPortfolioMode ? 'Sites Monitored' : 'Active Priorities'}
              </div>
              <div className="text-4xl font-bold text-white" data-testid="item-count">
                {itemCount}
              </div>
              {isPortfolioMode ? (
                <div className="text-sm text-slate-400 mt-1">
                  {portfolioData?.summary?.priority_count || 0} total priorities
                </div>
              ) : (
                <div className="flex gap-2 mt-1">
                  {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(band => (
                    <div key={band} className="flex items-center gap-1">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[band]}`}>
                        {totalDistribution[band] || 0}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Main Two-Column Layout */}
        <div className="grid grid-cols-5 gap-6">
          
          {/* ============================================ */}
          {/* SECTION 2: WHAT SHOULD I DO?                 */}
          {/* Operator: Ranked asset priorities             */}
          {/* Portfolio: Ranked sites by VaR                */}
          {/* ============================================ */}
          <section className="col-span-3" data-testid="actions-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">
                  {isPortfolioMode ? 'Sites Ranked by Risk' : 'Ranked Priorities'}
                </h2>
                <span className="text-xs text-emerald-400">
                  {isPortfolioMode ? `${portfolioData?.sites?.length || 0} sites` : (isConnected ? 'Live' : 'Updating...')}
                </span>
              </div>
              
              <div className="divide-y divide-slate-700/50 max-h-[480px] overflow-y-auto">
                {isPortfolioMode ? (
                  // PORTFOLIO: Site cards
                  (portfolioData?.sites || []).length === 0 ? (
                    <div className="p-8 text-center text-slate-500">No sites in scope</div>
                  ) : (
                    (portfolioData?.sites || []).map((site, idx) => (
                      <SiteCard
                        key={site.site_id}
                        site={site}
                        rank={idx + 1}
                        isFocus={portfolioData?.focus_site?.site_id === site.site_id}
                      />
                    ))
                  )
                ) : (
                  // OPERATOR: Priority cards
                  (wsPriorities?.length === 0) ? (
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
                  )
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
                  <div className="mb-4">
                    <div className="text-xs text-slate-400 mb-1">
                      {isPortfolioMode ? 'Portfolio Verified Savings' : 'Total Verified Savings'}
                    </div>
                    <div className="text-3xl font-bold text-emerald-400" data-testid="total-savings">
                      {formatCurrency(outcomesData?.total_savings || 0)}
                    </div>
                    <div className="text-sm text-slate-500">
                      {outcomesData?.verified_count || 0} outcomes verified
                    </div>
                  </div>
                  
                  {/* Recent Outcomes */}
                  <div className="space-y-2">
                    {isPortfolioMode ? (
                      // Portfolio: show per-site outcomes
                      (outcomesData?.site_outcomes || []).length === 0 ? (
                        <div className="text-center py-4 text-slate-500 text-sm">
                          No verified outcomes yet
                        </div>
                      ) : (
                        (outcomesData?.site_outcomes || []).map((so, idx) => (
                          <div key={idx} className="bg-slate-700/30 rounded-lg p-3">
                            <div className="flex items-center justify-between">
                              <span className="text-sm text-white">{so.site_name}</span>
                              <span className="text-sm font-semibold text-emerald-400">
                                +{formatCurrency(so.total_savings, 2)}
                              </span>
                            </div>
                            <div className="text-xs text-slate-500 mt-1">
                              {so.verified_count} verified outcome{so.verified_count !== 1 ? 's' : ''}
                            </div>
                          </div>
                        ))
                      )
                    ) : (
                      // Operator: show individual outcomes
                      (outcomesData?.outcomes || []).length === 0 ? (
                        <div className="text-center py-4 text-slate-500 text-sm">
                          No verified outcomes yet
                        </div>
                      ) : (
                        (outcomesData?.outcomes || []).slice(0, 3).map((outcome, idx) => (
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
                        ))
                      )
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
                  <TrustMetric
                    label="Verification Rate"
                    value={trustData?.verification_rate || 0}
                    format="percent"
                    description={isPortfolioMode ? "Actions verified across portfolio" : "Actions that reached verified outcome"}
                  />
                  <TrustMetric
                    label="Actions Validated"
                    value={trustData?.actions_validated || 0}
                    total={trustData?.total_actions || 0}
                    format="ratio"
                    description="Interventions with confirmed impact"
                  />
                  <TrustMetric
                    label="Learning Active"
                    value={trustData?.learning_improvement || 0}
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
          {isPortfolioMode ? (
            <span className="text-slate-500">Portfolio view</span>
          ) : (
            <ConnectionIndicator showLabel={true} />
          )}
        </div>
      </footer>
    </div>
  );
}

/**
 * Site Card — Portfolio mode
 * Replaces PriorityCard for portfolio users
 */
function SiteCard({ site, rank, isFocus }) {
  const totalPriorities = Object.values(site.distribution || {}).reduce((a, b) => a + b, 0);
  
  return (
    <div 
      className={`px-5 py-4 transition-colors ${
        isFocus 
          ? 'bg-amber-500/5 border-l-2 border-l-amber-500' 
          : 'hover:bg-slate-700/20'
      }`}
      data-testid={`site-card-${rank}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-slate-600 w-8">#{rank}</span>
          <div>
            <div className="flex items-center gap-2">
              {site.top_priority_band && (
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[site.top_priority_band]}`}>
                  {site.top_priority_band}
                </span>
              )}
              <span className="font-medium text-white" data-testid={`site-name-${rank}`}>
                {site.site_name}
              </span>
              {isFocus && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30" data-testid="focus-badge">
                  Focus
                </span>
              )}
            </div>
            <div className="text-sm text-slate-400 mt-0.5">
              {totalPriorities} active priorit{totalPriorities !== 1 ? 'ies' : 'y'}
            </div>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-lg font-semibold text-amber-400">
            {formatCurrency(site.var_per_day)}<span className="text-xs text-slate-400">/day</span>
          </div>
          <div className="text-xs text-slate-400">
            {formatCurrency(site.recoverable_per_day)} recoverable
          </div>
        </div>
      </div>
      
      {/* Priority distribution mini-bar */}
      {totalPriorities > 0 && (
        <div className="mt-3 ml-11 flex gap-2">
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(band => {
            const count = site.distribution?.[band] || 0;
            if (count === 0) return null;
            return (
              <div key={band} className="flex items-center gap-1">
                <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[band]}`}>
                  {count}
                </span>
                <span className="text-xs text-slate-500">{band.toLowerCase()}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Priority Card — Operator mode
 * With expandable traceability
 */
function PriorityCard({ priority, rank, isExpanded, onToggle, token }) {
  const [traceData, setTraceData] = useState(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  
  const economic = priority.economic_impact || {};
  const var_value = priority.value_at_risk_per_day || economic.value_at_risk_per_day || 0;
  const confidence = priority.confidence_label || 'unknown';
  
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
      
      {isExpanded && (
        <div className="mt-4 ml-11 border-l-2 border-slate-600 pl-4 space-y-3" data-testid="trace-chain">
          {loadingTrace ? (
            <div className="text-slate-500 text-sm">Loading trace...</div>
          ) : (
            <>
              <TraceStep
                label="State Detected"
                time={traceData?.state?.started_at || priority.created_at}
                detail={`${priority.state_type || 'Condition'} identified`}
                status="complete"
              />
              <TraceStep
                label="Priority Created"
                time={priority.created_at}
                detail={`${priority.priority_band} - Score ${priority.priority_score || 0}`}
                status="complete"
              />
              <TraceStep
                label="Intervention"
                time={traceData?.intervention?.created_at}
                detail={traceData?.intervention 
                  ? `${traceData.intervention.intervention_type} by ${traceData.intervention.created_by}`
                  : 'Awaiting action'
                }
                status={traceData?.intervention ? 'complete' : 'pending'}
              />
              <TraceStep
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
      
      <div className="mt-2 ml-11 text-xs text-slate-500">
        {isExpanded ? 'Collapse' : 'View trace'}
      </div>
    </div>
  );
}

function TraceStep({ label, time, detail, status }) {
  const isComplete = status === 'complete';
  return (
    <div className={`flex items-start gap-3 ${!isComplete ? 'opacity-50' : ''}`}>
      <div className={`w-2 h-2 rounded-full mt-1.5 ${isComplete ? 'bg-emerald-400' : 'bg-slate-600'}`} />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${isComplete ? 'text-white' : 'text-slate-400'}`}>
            {label}
          </span>
          {time && <span className="text-xs text-slate-500">{timeAgo(time)}</span>}
        </div>
        <div className="text-xs text-slate-400">{detail}</div>
      </div>
    </div>
  );
}

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
