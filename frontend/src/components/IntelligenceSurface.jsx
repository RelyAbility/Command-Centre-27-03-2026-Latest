/**
 * Industrial Intelligence Surface
 * ================================
 * 
 * Single-page unified dashboard — Rockwell demo.
 * 
 * TWO modes, ONE surface:
 * 
 * OPERATOR MODE (HOW lens):
 *   Asset-level priorities, action-focused, WebSocket real-time
 * 
 * PORTFOLIO MODE (WHERE lens):
 *   Portfolio Analysis → RAMP Action → Verified Outcome
 *   "We analysed 400 assets… here's where the money is…
 *    and here's proof we can capture it"
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
  strong: 'text-emerald-400', HIGH: 'text-emerald-400',
  moderate: 'text-yellow-400', MEDIUM: 'text-yellow-400',
  low: 'text-orange-400', LOW: 'text-orange-400',
  unknown: 'text-slate-400',
};

const STATE_COLORS = {
  stable: 'bg-emerald-500',
  drift: 'bg-amber-500',
  idle: 'bg-slate-400',
  cycling: 'bg-orange-500',
  degraded: 'bg-red-500',
};

const fmt = (v, d = 0) => {
  if (v == null) return '$0';
  return `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`;
};

const fmtCompact = (v) => {
  if (v >= 1000000) return `$${(v / 1000000).toFixed(1)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}k`;
  return fmt(v);
};

const timeAgo = (date) => {
  if (!date) return 'N/A';
  const d = Math.floor((new Date() - new Date(date)) / 60000);
  if (d < 60) return `${d}m ago`;
  if (d < 1440) return `${Math.floor(d / 60)}h ago`;
  return `${Math.floor(d / 1440)}d ago`;
};


/* ========================================================================= */
/* MAIN COMPONENT                                                            */
/* ========================================================================= */

export function IntelligenceSurface() {
  const { token, user, signOut, canAccessHOW, canAccessWHERE } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedPriority, setExpandedPriority] = useState(null);
  const [expandedSite, setExpandedSite] = useState(null);

  const isPortfolioMode = canAccessWHERE && !canAccessHOW;

  const { priorities: wsPriorities, isConnected } = useRAMPWebSocket(
    canAccessHOW ? token : null,
    { autoConnect: canAccessHOW }
  );

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      try {
        if (isPortfolioMode) {
          const [portfolioRes, analysisRes] = await Promise.all([
            axios.get(`${API}/where/portfolio/intelligence`, { headers: { Authorization: `Bearer ${token}` } }),
            axios.get(`${API}/iba/refrigeration/analysis`, { headers: { Authorization: `Bearer ${token}` } }),
          ]);
          setPortfolioData(portfolioRes.data);
          setAnalysisData(analysisRes.data);
        } else {
          const [summaryRes, outcomesRes, trustRes] = await Promise.all([
            axios.get(`${API}/intelligence/summary`, { headers: { Authorization: `Bearer ${token}` } }),
            axios.get(`${API}/intelligence/outcomes`, { headers: { Authorization: `Bearer ${token}` } }),
            axios.get(`${API}/intelligence/trust`, { headers: { Authorization: `Bearer ${token}` } }),
          ]);
          setMetrics({ summary: summaryRes.data, outcomes: outcomesRes.data, trust: trustRes.data });
        }
      } catch (e) {
        console.error('Failed to fetch intelligence data:', e);
      }
      setLoading(false);
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [token, isPortfolioMode]);

  const priorityMetrics = useMemo(() => {
    if (isPortfolioMode || !wsPriorities || wsPriorities.length === 0)
      return { totalVAR: 0, totalRecoverable: 0, count: 0, distribution: {} };
    let totalVAR = 0, totalRecoverable = 0;
    const dist = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    wsPriorities.forEach(p => {
      const eco = p.economic_impact || {};
      totalVAR += p.value_at_risk_per_day || eco.value_at_risk_per_day || 0;
      totalRecoverable += p.value_recoverable_per_day || eco.value_recoverable_per_day || 0;
      dist[p.priority_band] = (dist[p.priority_band] || 0) + 1;
    });
    return { totalVAR, totalRecoverable, count: wsPriorities.length, distribution: dist };
  }, [wsPriorities, isPortfolioMode]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400" data-testid="loading-indicator">Loading intelligence surface...</div>
      </div>
    );
  }

  const varTotal = isPortfolioMode ? (portfolioData?.summary?.total_var || 0) : priorityMetrics.totalVAR;
  const recoverableTotal = isPortfolioMode ? (portfolioData?.summary?.total_recoverable || 0) : priorityMetrics.totalRecoverable;
  const outcomesData = isPortfolioMode ? portfolioData?.outcomes : metrics?.outcomes;
  const trustData = isPortfolioMode ? portfolioData?.trust : metrics?.trust;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 pb-12">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold tracking-tight">
              RAMP <span className="text-slate-400 font-normal">Industrial Intelligence</span>
            </h1>
            {isPortfolioMode ? (
              <span className="text-xs px-2.5 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300" data-testid="mode-badge">Portfolio</span>
            ) : (
              <ConnectionIndicator />
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400" data-testid="user-email">{user?.email}</span>
            <button onClick={signOut} className="text-sm text-slate-400 hover:text-white" data-testid="sign-out-btn">Sign Out</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {isPortfolioMode ? (
          <PortfolioView
            portfolioData={portfolioData}
            analysisData={analysisData}
            varTotal={varTotal}
            recoverableTotal={recoverableTotal}
            outcomesData={outcomesData}
            trustData={trustData}
            expandedSite={expandedSite}
            setExpandedSite={setExpandedSite}
          />
        ) : (
          <OperatorView
            priorityMetrics={priorityMetrics}
            wsPriorities={wsPriorities}
            isConnected={isConnected}
            outcomesData={outcomesData}
            trustData={trustData}
            expandedPriority={expandedPriority}
            setExpandedPriority={setExpandedPriority}
            token={token}
            varTotal={varTotal}
            recoverableTotal={recoverableTotal}
          />
        )}
      </main>

      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800/80 backdrop-blur-sm border-t border-slate-700/50 px-6 py-2 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-500">
          <span>RAMP Industrial Intelligence</span>
          {isPortfolioMode ? (
            <span>{portfolioData?.summary?.site_count || 0} sites &middot; {portfolioData?.summary?.total_assets || 0} assets &middot; Portfolio view</span>
          ) : (
            <ConnectionIndicator showLabel={true} />
          )}
        </div>
      </footer>
    </div>
  );
}


/* ========================================================================= */
/* PORTFOLIO VIEW — Analysis → Action → Proof                               */
/* ========================================================================= */

function PortfolioView({ portfolioData, analysisData, varTotal, recoverableTotal, outcomesData, trustData, expandedSite, setExpandedSite }) {
  const fleet = analysisData?.fleet;
  const scale = analysisData?.scale;
  const stateDist = analysisData?.state_distribution;
  const opportunities = analysisData?.opportunities || [];
  const siteRanking = analysisData?.site_ranking || [];
  const highlight = analysisData?.highlight;
  const rampConnection = analysisData?.ramp_connection;
  const benchmarks = analysisData?.benchmarks;

  return (
    <div className="space-y-5">

      {/* ================================================================ */}
      {/* PORTFOLIO ANALYSIS — Fleet Overview + Scale                      */}
      {/* ================================================================ */}
      {fleet && (
        <section data-testid="portfolio-analysis">
          <div className="bg-gradient-to-r from-slate-800 via-slate-800 to-slate-800/80 rounded-xl border border-slate-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs text-indigo-400 uppercase tracking-wider font-medium">Portfolio Analysis</div>
                <div className="text-sm text-slate-400 mt-0.5">
                  {fleet.total_units} refrigeration units &middot; {fleet.site_count} sites &middot; {fleet.analysis_days}-day analysis
                </div>
              </div>
              <div className="text-xs text-slate-500 italic" data-testid="trust-signal">
                {analysisData?.trust_signal}
              </div>
            </div>

            {/* Scale Numbers */}
            <div className="grid grid-cols-4 gap-3 mb-5">
              <div className="bg-slate-900/50 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-0.5">30-Day Opportunity</div>
                <div className="text-2xl font-bold text-white" data-testid="opp-30day">{fmtCompact(scale?.total_30day || 0)}</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-0.5">Annualized Impact</div>
                <div className="text-2xl font-bold text-emerald-400" data-testid="opp-annual">{fmtCompact(scale?.annualized || 0)}</div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-0.5">Live VaR (RAMP sites)</div>
                <div className="text-2xl font-bold text-red-400" data-testid="total-var">{fmt(varTotal)}<span className="text-sm text-red-400/60">/day</span></div>
              </div>
              <div className="bg-slate-900/50 rounded-lg p-3">
                <div className="text-xs text-slate-400 mb-0.5">Recoverable</div>
                <div className="text-2xl font-bold text-emerald-400" data-testid="total-recoverable">{fmt(recoverableTotal)}<span className="text-sm text-emerald-400/60">/day</span></div>
              </div>
            </div>

            {/* State Distribution Bar */}
            {stateDist && (
              <div data-testid="state-distribution">
                <div className="text-xs text-slate-400 uppercase tracking-wider mb-2">Fleet State Distribution</div>
                <div className="flex h-6 rounded-lg overflow-hidden gap-px">
                  {['stable', 'drift', 'idle', 'cycling', 'degraded'].map(s => {
                    const pct = stateDist[s]?.percent || 0;
                    if (pct < 1) return null;
                    return (
                      <div key={s} className={`${STATE_COLORS[s]} relative group`} style={{ width: `${pct}%` }}
                        title={`${s}: ${stateDist[s]?.count} units (${pct}%)`}>
                        {pct > 8 && (
                          <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white/90">
                            {pct}%
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-4 mt-2">
                  {['stable', 'drift', 'idle', 'cycling', 'degraded'].map(s => (
                    <div key={s} className="flex items-center gap-1.5">
                      <div className={`w-2.5 h-2.5 rounded-sm ${STATE_COLORS[s]}`} />
                      <span className="text-xs text-slate-400 capitalize">{s}</span>
                      <span className="text-xs text-slate-500">{stateDist[s]?.count || 0}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/* TOP OPPORTUNITIES                                                */}
      {/* ================================================================ */}
      {opportunities.length > 0 && (
        <section data-testid="opportunities-section">
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Top Opportunities</h2>
              <span className="text-xs text-emerald-400">{fmtCompact(scale?.annualized || 0)}/yr total</span>
            </div>
            <div className="divide-y divide-slate-700/50">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="px-5 py-3 flex items-center justify-between" data-testid={`opportunity-${idx}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-slate-600 w-6">#{idx + 1}</span>
                    <div>
                      <div className="text-sm font-medium text-white">{opp.category}</div>
                      <div className="text-xs text-slate-500">{opp.description}</div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <div className="text-sm font-semibold text-amber-400">{fmtCompact(opp.monthly_impact)}/mo</div>
                    <div className="text-xs text-slate-500">{opp.affected_assets} assets &middot; {fmtCompact(opp.annual_impact)}/yr</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/* ANALYSIS → ACTION CONNECTOR                                      */}
      {/* ================================================================ */}
      {rampConnection && rampConnection.active_detection && (
        <section data-testid="ramp-connector">
          <div className="bg-gradient-to-r from-indigo-900/30 via-indigo-900/15 to-slate-800 rounded-xl border border-indigo-500/20 p-5">
            <div className="text-xs text-indigo-400 uppercase tracking-wider font-medium mb-3">
              Portfolio Analysis &rarr; Live Detection
            </div>
            <p className="text-sm text-slate-300 mb-4">{rampConnection.message}</p>

            <div className="flex items-stretch gap-3">
              {/* Active Detection */}
              <div className="flex-1 bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
                <div className="text-xs text-red-400 uppercase tracking-wider mb-2">Active Detection</div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[rampConnection.active_detection.priority_band]}`}>
                    {rampConnection.active_detection.priority_band}
                  </span>
                  <span className="text-sm font-medium text-white">{rampConnection.active_detection.asset_name}</span>
                </div>
                <div className="text-xs text-slate-400">{rampConnection.active_detection.site_name}</div>
                <div className="text-xs text-slate-500 mt-1">{rampConnection.active_detection.condition}</div>
                <div className="text-lg font-semibold text-amber-400 mt-2">
                  {fmt(rampConnection.active_detection.var_per_day)}<span className="text-xs text-slate-400">/day at risk</span>
                </div>
              </div>

              {/* Arrow */}
              <div className="flex items-center px-2">
                <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </div>

              {/* Verified Proof */}
              <div className="flex-1 bg-slate-900/50 rounded-lg p-4 border border-emerald-500/20">
                <div className="text-xs text-emerald-400 uppercase tracking-wider mb-2">Verified Outcome</div>
                {rampConnection.verified_proof ? (
                  <>
                    <div className="text-sm font-medium text-white mb-1">{rampConnection.verified_proof.asset_name}</div>
                    <div className="text-xs text-slate-400">{rampConnection.verified_proof.site_name}</div>
                    <div className="text-lg font-semibold text-emerald-400 mt-2">
                      +{rampConnection.verified_proof.savings_value} {rampConnection.verified_proof.savings_unit}
                      <span className="text-xs text-slate-400 ml-1">saved</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{timeAgo(rampConnection.verified_proof.verified_at)}</div>
                  </>
                ) : (
                  <div className="text-sm text-slate-500">Pending verification</div>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/* TWO-COLUMN: Site Ranking + Outcomes/Trust/Benchmarks             */}
      {/* ================================================================ */}
      <div className="grid grid-cols-5 gap-5">

        {/* Left: Site Ranking (from IBA) */}
        <section className="col-span-3 space-y-5" data-testid="actions-section">
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Sites Ranked by Opportunity</h2>
              <span className="text-xs text-slate-400">{siteRanking.length} sites</span>
            </div>
            <div className="divide-y divide-slate-700/50">
              {siteRanking.map((site, idx) => (
                <AnalysisSiteCard
                  key={site.site_id}
                  site={site}
                  rank={idx + 1}
                  isHighlight={highlight?.site?.site_id === site.site_id}
                  isExpanded={expandedSite === site.site_id}
                  onToggle={() => setExpandedSite(expandedSite === site.site_id ? null : site.site_id)}
                  rampSites={portfolioData?.sites || []}
                />
              ))}
            </div>
          </div>
        </section>

        {/* Right: Outcomes + Trust + Benchmarks */}
        <div className="col-span-2 space-y-5">

          {/* Verified Outcomes (with scaling) */}
          <section data-testid="outcomes-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Verified Outcomes</h2>
              </div>
              <div className="p-5">
                <div className="mb-3">
                  <div className="text-xs text-slate-400 mb-1">Portfolio Verified Savings</div>
                  <div className="text-3xl font-bold text-emerald-400" data-testid="total-savings">{fmt(outcomesData?.total_savings || 0, 2)}</div>
                  <div className="text-sm text-slate-500">{outcomesData?.verified_count || 0} outcomes verified</div>
                </div>
                {(outcomesData?.scaled_outcomes || []).length > 0 && (
                  <div className="mb-3 bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3" data-testid="scaled-outcomes">
                    <div className="text-xs text-emerald-400 uppercase tracking-wider mb-2">Scalable Across Portfolio</div>
                    {outcomesData.scaled_outcomes.map((so, idx) => (
                      <div key={idx} className="flex items-center justify-between py-1">
                        <span className="text-sm text-slate-300">
                          <span className="text-emerald-400 font-semibold">{so.verified_savings} {so.savings_unit}</span>
                          <span className="text-slate-500"> verified</span>
                        </span>
                        <span className="text-sm text-white font-semibold">
                          &rarr; {so.scaled_potential} {so.scaled_potential_unit}
                          <span className="text-xs text-slate-500 ml-1">({so.similar_assets_in_portfolio} similar)</span>
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {(outcomesData?.site_outcomes || []).map((so, idx) => (
                  <div key={idx} className="bg-slate-700/30 rounded-lg p-3 mb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-white">{so.site_name}</span>
                      <span className="text-sm font-semibold text-emerald-400">+{fmt(so.total_savings, 2)}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{so.verified_count} verified</div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* System Trust */}
          <section data-testid="trust-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">System Trust</h2>
              </div>
              <div className="p-5 space-y-4">
                <TrustMetric label="Verification Rate" value={trustData?.verification_rate || 0} format="percent"
                  description="Actions verified across portfolio" />
                <TrustMetric label="Actions Validated" value={trustData?.actions_validated || 0}
                  total={trustData?.total_actions || 0} format="ratio" description="Interventions with confirmed impact" />
                <TrustMetric label="Learning Active" value={trustData?.learning_improvement || 0} format="percent"
                  description="Outcomes improving baseline accuracy" positive />
              </div>
            </div>
          </section>

          {/* Fleet Benchmarks */}
          {benchmarks && (
            <section data-testid="benchmarks-section">
              <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-700">
                  <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Fleet Benchmarks</h2>
                </div>
                <div className="p-5 space-y-4">
                  <BenchmarkBar label="Energy Intensity" unit={benchmarks.energy_intensity.unit}
                    p25={benchmarks.energy_intensity.p25} p50={benchmarks.energy_intensity.p50} p75={benchmarks.energy_intensity.p75} />
                  <BenchmarkBar label="Runtime Ratio" unit=""
                    p25={benchmarks.runtime_ratio.p25} p50={benchmarks.runtime_ratio.p50} p75={benchmarks.runtime_ratio.p75} />
                  <BenchmarkBar label="Cycle Frequency" unit={benchmarks.cycle_frequency.unit}
                    p25={benchmarks.cycle_frequency.p25} p50={benchmarks.cycle_frequency.p50} p75={benchmarks.cycle_frequency.p75} />
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}


/* ========================================================================= */
/* ANALYSIS SITE CARD — IBA site with inline RAMP drill-down                */
/* ========================================================================= */

function AnalysisSiteCard({ site, rank, isHighlight, isExpanded, onToggle, rampSites }) {
  const rampSite = rampSites.find(rs => rs.site_id === site.site_id);
  const hasRampData = rampSite && rampSite.top_priorities?.length > 0;
  const sd = site.state_distribution || {};

  return (
    <div className={`transition-colors cursor-pointer ${isHighlight ? 'bg-amber-500/5' : 'hover:bg-slate-700/20'}`}
      onClick={onToggle} data-testid={`site-card-${rank}`}>
      <div className={`px-5 py-4 ${isHighlight ? 'border-l-2 border-l-amber-500' : ''}`}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold text-slate-600 w-8">#{rank}</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-white" data-testid={`site-name-${rank}`}>{site.site_name}</span>
                {isHighlight && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30" data-testid="focus-badge">Top Opportunity</span>
                )}
                {site.ramp_live && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">RAMP Live</span>
                )}
              </div>
              <div className="text-sm text-slate-400 mt-0.5">
                {site.unit_count} units &middot; {site.non_stable_pct}% non-stable
              </div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold text-amber-400">{fmtCompact(site.monthly_opportunity)}<span className="text-xs text-slate-400">/mo</span></div>
            <div className="text-xs text-slate-400">{fmtCompact(site.annual_opportunity)}/yr</div>
          </div>
        </div>

        {/* Mini state distribution */}
        <div className="mt-2 ml-11 flex gap-2">
          {['degraded', 'drift', 'cycling', 'idle', 'stable'].map(s => {
            const cnt = sd[s] || 0;
            if (cnt === 0) return null;
            return (
              <div key={s} className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-sm ${STATE_COLORS[s]}`} />
                <span className="text-xs text-slate-500">{cnt} {s}</span>
              </div>
            );
          })}
        </div>
        <div className="mt-2 ml-11 text-xs text-slate-500">{isExpanded ? 'Collapse' : (hasRampData ? 'View live priorities' : 'View details')}</div>
      </div>

      {/* Inline Drill-Down */}
      {isExpanded && hasRampData && (
        <div className="mx-5 mb-4 ml-16 border-l-2 border-indigo-500/30 pl-4 space-y-2" data-testid={`site-drilldown-${rank}`}>
          <div className="text-xs text-indigo-400 uppercase tracking-wider mb-1">Live RAMP Priorities</div>
          {rampSite.top_priorities.map((p, idx) => (
            <div key={idx} className="flex items-center justify-between bg-slate-700/20 rounded-lg px-3 py-2">
              <div className="flex items-center gap-2">
                <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[p.priority_band]}`}>{p.priority_band}</span>
                <div>
                  <div className="text-sm text-white">{p.asset_name}</div>
                  <div className="text-xs text-slate-500">{p.driver}</div>
                </div>
              </div>
              <div className="text-right shrink-0 ml-3">
                <div className="text-sm font-semibold text-amber-400">{fmt(p.var_per_day)}<span className="text-xs text-slate-400">/day</span></div>
                {p.confidence && (
                  <div className={`text-xs capitalize ${CONFIDENCE_COLORS[p.confidence] || CONFIDENCE_COLORS.unknown}`}>{p.confidence} confidence</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {isExpanded && !hasRampData && (
        <div className="mx-5 mb-4 ml-16 border-l-2 border-slate-600 pl-4" data-testid={`site-drilldown-${rank}`}>
          <div className="text-xs text-slate-500">Analysis-only site — not yet monitored by RAMP in real-time</div>
        </div>
      )}
    </div>
  );
}


/* ========================================================================= */
/* OPERATOR VIEW — Unchanged from existing                                  */
/* ========================================================================= */

function OperatorView({ priorityMetrics, wsPriorities, isConnected, outcomesData, trustData, expandedPriority, setExpandedPriority, token, varTotal, recoverableTotal }) {
  return (
    <>
      <section className="mb-6" data-testid="var-section">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gradient-to-br from-red-900/30 to-slate-800 rounded-xl border border-red-800/30 p-5">
            <div className="text-xs text-red-400 uppercase tracking-wider mb-1">Value at Risk</div>
            <div className="text-4xl font-bold text-red-400" data-testid="total-var">{fmt(varTotal)}<span className="text-lg text-red-400/60">/day</span></div>
            <div className="text-sm text-slate-400 mt-1">{fmt(varTotal * 365)} annual exposure</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-900/30 to-slate-800 rounded-xl border border-emerald-800/30 p-5">
            <div className="text-xs text-emerald-400 uppercase tracking-wider mb-1">Recoverable Value</div>
            <div className="text-4xl font-bold text-emerald-400" data-testid="total-recoverable">{fmt(recoverableTotal)}<span className="text-lg text-emerald-400/60">/day</span></div>
            <div className="text-sm text-slate-400 mt-1">{((recoverableTotal / (varTotal || 1)) * 100).toFixed(0)}% of VAR addressable</div>
          </div>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
            <div className="text-xs text-slate-400 uppercase tracking-wider mb-2">Active Priorities</div>
            <div className="text-4xl font-bold text-white" data-testid="item-count">{priorityMetrics.count}</div>
            <div className="flex gap-2 mt-1">
              {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(b => (
                <span key={b} className={`px-1.5 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[b]}`}>{priorityMetrics.distribution[b] || 0}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-5 gap-6">
        <section className="col-span-3" data-testid="actions-section">
          <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Ranked Priorities</h2>
              <span className="text-xs text-emerald-400">{isConnected ? 'Live' : 'Updating...'}</span>
            </div>
            <div className="divide-y divide-slate-700/50">
              {(wsPriorities?.length === 0) ? (
                <div className="p-8 text-center text-slate-500">No active priorities</div>
              ) : (
                wsPriorities?.map((p, idx) => (
                  <PriorityCard key={p.priority_id || p.id || idx} priority={p} rank={idx + 1}
                    isExpanded={expandedPriority === (p.priority_id || p.id)}
                    onToggle={() => setExpandedPriority(expandedPriority === (p.priority_id || p.id) ? null : (p.priority_id || p.id))}
                    token={token} />
                ))
              )}
            </div>
          </div>
        </section>

        <div className="col-span-2 space-y-5">
          <section data-testid="outcomes-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Verified Outcomes</h2>
              </div>
              <div className="p-5">
                <div className="text-xs text-slate-400 mb-1">Total Verified Savings</div>
                <div className="text-3xl font-bold text-emerald-400 mb-1" data-testid="total-savings">{fmt(outcomesData?.total_savings || 0, 2)}</div>
                <div className="text-sm text-slate-500 mb-3">{outcomesData?.verified_count || 0} outcomes verified</div>
                {(outcomesData?.outcomes || []).slice(0, 3).map((o, i) => (
                  <div key={i} className="bg-slate-700/30 rounded-lg p-3 mb-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-white">{o.asset_name || 'Asset'}</span>
                      <span className="text-sm font-semibold text-emerald-400">+{o.savings_value} {o.savings_unit}</span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-slate-500">{timeAgo(o.verified_at)}</span>
                      <span className={`text-xs capitalize ${CONFIDENCE_COLORS[o.confidence_band?.toLowerCase()] || CONFIDENCE_COLORS.unknown}`}>{o.confidence_band || 'Unknown'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
          <section data-testid="trust-section">
            <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
              <div className="px-5 py-3 border-b border-slate-700">
                <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">System Trust</h2>
              </div>
              <div className="p-5 space-y-4">
                <TrustMetric label="Verification Rate" value={trustData?.verification_rate || 0} format="percent" description="Actions that reached verified outcome" />
                <TrustMetric label="Actions Validated" value={trustData?.actions_validated || 0} total={trustData?.total_actions || 0} format="ratio" description="Interventions with confirmed impact" />
                <TrustMetric label="Learning Active" value={trustData?.learning_improvement || 0} format="percent" description="Outcomes improving baseline accuracy" positive />
              </div>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}


/* ========================================================================= */
/* PRIORITY CARD — Operator mode with traceability                           */
/* ========================================================================= */

function PriorityCard({ priority, rank, isExpanded, onToggle, token }) {
  const [traceData, setTraceData] = useState(null);
  const [loadingTrace, setLoadingTrace] = useState(false);
  const eco = priority.economic_impact || {};
  const varVal = priority.value_at_risk_per_day || eco.value_at_risk_per_day || 0;
  const conf = priority.confidence_label || 'unknown';

  useEffect(() => {
    if (isExpanded && !traceData && !loadingTrace) {
      setLoadingTrace(true);
      axios.get(`${API}/intelligence/trace/${priority.state_id}`, { headers: { Authorization: `Bearer ${token}` } })
        .then(res => setTraceData(res.data))
        .catch(() => setTraceData({}))
        .finally(() => setLoadingTrace(false));
    }
  }, [isExpanded, traceData, loadingTrace, priority, token]);

  return (
    <div className="px-5 py-4 hover:bg-slate-700/20 cursor-pointer" onClick={onToggle} data-testid={`priority-card-${rank}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-slate-600 w-8">#{rank}</span>
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[priority.priority_band]}`}>{priority.priority_band}</span>
              <span className="font-medium text-white">{priority.asset_name || priority.asset_id}</span>
            </div>
            <div className="text-sm text-slate-400 mt-0.5">{priority.drivers?.[0] || priority.state_type || 'Active condition'}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-semibold text-amber-400">{fmt(varVal)}<span className="text-xs text-slate-400">/day</span></div>
          <div className={`text-xs capitalize ${CONFIDENCE_COLORS[conf.toLowerCase()] || CONFIDENCE_COLORS.unknown}`}>{conf} confidence</div>
        </div>
      </div>
      {isExpanded && (
        <div className="mt-4 ml-11 border-l-2 border-slate-600 pl-4 space-y-3" data-testid="trace-chain">
          {loadingTrace ? <div className="text-slate-500 text-sm">Loading trace...</div> : (
            <>
              <TraceStep label="State Detected" time={traceData?.state?.started_at || priority.created_at} detail={`${priority.state_type || 'Condition'} identified`} status="complete" />
              <TraceStep label="Priority Created" time={priority.created_at} detail={`${priority.priority_band} - Score ${priority.priority_score || 0}`} status="complete" />
              <TraceStep label="Intervention" time={traceData?.intervention?.created_at}
                detail={traceData?.intervention ? `${traceData.intervention.intervention_type} by ${traceData.intervention.created_by}` : 'Awaiting action'}
                status={traceData?.intervention ? 'complete' : 'pending'} />
              <TraceStep label="Outcome Verified" time={traceData?.outcome?.verified_at}
                detail={traceData?.outcome ? `${traceData.outcome.savings_value} ${traceData.outcome.savings_unit} saved` : 'Pending verification'}
                status={traceData?.outcome ? 'complete' : 'pending'} />
            </>
          )}
        </div>
      )}
      <div className="mt-2 ml-11 text-xs text-slate-500">{isExpanded ? 'Collapse' : 'View trace'}</div>
    </div>
  );
}


/* ========================================================================= */
/* SMALL COMPONENTS                                                          */
/* ========================================================================= */

function TraceStep({ label, time, detail, status }) {
  const ok = status === 'complete';
  return (
    <div className={`flex items-start gap-3 ${!ok ? 'opacity-50' : ''}`}>
      <div className={`w-2 h-2 rounded-full mt-1.5 ${ok ? 'bg-emerald-400' : 'bg-slate-600'}`} />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className={`text-sm font-medium ${ok ? 'text-white' : 'text-slate-400'}`}>{label}</span>
          {time && <span className="text-xs text-slate-500">{timeAgo(time)}</span>}
        </div>
        <div className="text-xs text-slate-400">{detail}</div>
      </div>
    </div>
  );
}

function TrustMetric({ label, value, total, format, description, positive }) {
  let display;
  if (format === 'percent') display = `${(value * 100).toFixed(0)}%`;
  else if (format === 'ratio' && total !== undefined) display = `${value}/${total}`;
  else display = value;
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-300">{label}</span>
        <span className={`text-lg font-semibold ${positive ? 'text-emerald-400' : 'text-white'}`}>{display}</span>
      </div>
      {format === 'percent' && (
        <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${positive ? 'bg-emerald-500' : 'bg-slate-400'}`} style={{ width: `${Math.min(value * 100, 100)}%` }} />
        </div>
      )}
      <div className="text-xs text-slate-500 mt-1">{description}</div>
    </div>
  );
}

function BenchmarkBar({ label, unit, p25, p50, p75 }) {
  const range = p75 - p25;
  const max = p75 + range * 0.5;
  const min = Math.max(0, p25 - range * 0.3);
  const total = max - min;
  const leftPct = ((p25 - min) / total) * 100;
  const widthPct = (range / total) * 100;
  const midPct = ((p50 - min) / total) * 100;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-300">{label}</span>
        <span className="text-xs text-slate-500">{unit}</span>
      </div>
      <div className="relative h-4 bg-slate-700 rounded-full overflow-hidden">
        <div className="absolute top-0 h-full bg-emerald-500/20 rounded-full"
          style={{ left: `${leftPct}%`, width: `${widthPct}%` }} />
        <div className="absolute top-0 w-0.5 h-full bg-emerald-400"
          style={{ left: `${midPct}%` }} />
      </div>
      <div className="flex justify-between mt-1 text-xs text-slate-500">
        <span>P25: {p25}</span>
        <span className="text-emerald-400 font-medium">P50: {p50}</span>
        <span>P75: {p75}</span>
      </div>
    </div>
  );
}

export default IntelligenceSurface;
