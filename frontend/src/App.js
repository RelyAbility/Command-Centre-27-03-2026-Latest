import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Band colors
const BAND_COLORS = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-black",
  LOW: "bg-blue-500 text-white",
};

const CONFIDENCE_COLORS = {
  HIGH: "text-emerald-400",
  MEDIUM: "text-yellow-400",
  LOW: "text-orange-400",
  INSUFFICIENT: "text-red-400",
};

const INTEGRITY_COLORS = {
  HEALTHY: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  DEGRADED: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  POOR: "text-red-400 bg-red-500/10 border-red-500/20",
};

function App() {
  const [valueSummary, setValueSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [showIntervention, setShowIntervention] = useState(false);
  const [selectedAction, setSelectedAction] = useState(null);
  const [interventionForm, setInterventionForm] = useState({
    type: "ADJUSTMENT",
    description: "",
  });
  const [message, setMessage] = useState(null);

  // Fetch value summary
  const fetchValueSummary = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/system/value-summary`);
      setValueSummary(res.data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (e) {
      console.error("Failed to fetch value summary", e);
      setLoading(false);
    }
  }, []);

  // Create intervention
  const createIntervention = async () => {
    if (!selectedAction) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/how/interventions`, {
        state_id: selectedAction.state_id,
        intervention_type: interventionForm.type,
        description: interventionForm.description,
        created_by: "operator@ramp.io",
      });
      setMessage({
        type: "success",
        text: "Intervention created. Baseline frozen for verification.",
      });
      setShowIntervention(false);
      setSelectedAction(null);
      setInterventionForm({ type: "ADJUSTMENT", description: "" });
      await fetchValueSummary();
    } catch (e) {
      setMessage({ type: "error", text: "Failed to create intervention" });
    }
    setLoading(false);
  };

  // Demo: Simulate full flow
  const runFullDemo = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/system/demo/complete-verification-flow`);
      setMessage({
        type: "success",
        text: "Full verification flow completed",
      });
      await fetchValueSummary();
    } catch (e) {
      setMessage({ type: "error", text: "Failed to run demo" });
    }
    setLoading(false);
  };

  // Initial load and polling
  useEffect(() => {
    fetchValueSummary();
    const interval = setInterval(fetchValueSummary, 30000);
    return () => clearInterval(interval);
  }, [fetchValueSummary]);

  // Clear message
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  if (loading && !valueSummary) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  const { value_at_risk, top_actions, recovered_value, loop_integrity, currency } = valueSummary || {};

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold tracking-tight">
                RAMP <span className="text-slate-400 font-normal">Value Dashboard</span>
              </h1>
              {loop_integrity && (
                <span
                  className={`text-xs px-2.5 py-1 rounded-full border ${INTEGRITY_COLORS[loop_integrity.status]}`}
                  data-testid="loop-status"
                >
                  Loop {loop_integrity.status}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              {lastUpdate && (
                <span className="text-xs text-slate-500">
                  Updated {lastUpdate.toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={runFullDemo}
                disabled={loading}
                className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-50"
                data-testid="run-demo-btn"
              >
                Run Demo
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Message Toast */}
      {message && (
        <div
          className={`fixed top-20 right-6 px-4 py-3 rounded-lg shadow-lg z-50 ${
            message.type === "success" ? "bg-emerald-600" : "bg-red-600"
          }`}
          data-testid="message-toast"
        >
          {message.text}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Top Row: Value at Risk + Loop Integrity */}
        <div className="grid grid-cols-3 gap-6 mb-8">
          {/* VALUE AT RISK - Hero Card */}
          <div className="col-span-2 bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-2xl border border-slate-700/50 p-6">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-1">
                  Value at Risk
                </h2>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold text-amber-400" data-testid="total-var">
                    ${value_at_risk?.total_per_day?.toLocaleString() || "0"}
                  </span>
                  <span className="text-xl text-slate-400">/day</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-slate-400">
                  {value_at_risk?.active_priorities || 0} active priorities
                </div>
              </div>
            </div>
            
            {/* VaR by Band */}
            <div className="flex gap-4">
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((band) => {
                const amount = value_at_risk?.breakdown_by_band?.[band] || 0;
                if (amount === 0) return null;
                return (
                  <div key={band} className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[band]}`}>
                      {band}
                    </span>
                    <span className="text-sm text-slate-300">
                      ${amount.toFixed(0)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* LOOP INTEGRITY */}
          <div className="bg-slate-800 rounded-2xl border border-slate-700/50 p-6">
            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-4">
              Loop Integrity
            </h2>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Verified</span>
                <span className="text-emerald-400 font-semibold" data-testid="verified-count">
                  {loop_integrity?.verified || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Pending</span>
                <span className="text-yellow-400 font-semibold" data-testid="pending-count">
                  {loop_integrity?.pending || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-300">Insufficient</span>
                <span className="text-red-400 font-semibold" data-testid="insufficient-count">
                  {loop_integrity?.insufficient_data || 0}
                </span>
              </div>
              
              {loop_integrity?.verification_rate_percent !== null && (
                <div className="pt-3 border-t border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Verification Rate</span>
                    <span className={`font-semibold ${
                      loop_integrity.verification_rate_percent >= 70 ? "text-emerald-400" :
                      loop_integrity.verification_rate_percent >= 40 ? "text-yellow-400" : "text-red-400"
                    }`}>
                      {loop_integrity.verification_rate_percent}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Middle Row: Top Actions + Recovered Value */}
        <div className="grid grid-cols-2 gap-6">
          {/* TOP ACTIONS */}
          <div className="bg-slate-800 rounded-2xl border border-slate-700/50 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                Top Priority Actions
              </h2>
              <span className="text-xs text-slate-500">
                Value recoverable with action
              </span>
            </div>
            
            {top_actions?.length > 0 ? (
              <div className="space-y-3" data-testid="top-actions-list">
                {top_actions.map((action, idx) => (
                  <div
                    key={action.priority_id}
                    className="bg-slate-700/30 rounded-xl p-4 border border-slate-700/50 hover:border-slate-600 transition-colors"
                    data-testid={`action-${idx}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[action.priority_band]}`}>
                          {action.priority_band}
                        </span>
                        <span className="font-medium text-white">
                          {action.asset_name}
                        </span>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-amber-400">
                          ${action.value_at_risk_per_day?.toFixed(0) || "0"}
                          <span className="text-xs text-slate-400">/day</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm text-slate-400">
                          {action.state_family}:{action.state_type}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {action.drivers?.join(" • ")}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <div className={`text-sm font-medium ${CONFIDENCE_COLORS[action.confidence_band]}`}>
                            {action.confidence_band}
                          </div>
                          <div className="text-xs text-slate-500">
                            {(action.confidence * 100).toFixed(0)}% conf
                          </div>
                        </div>
                        <button
                          onClick={() => {
                            setSelectedAction(action);
                            setShowIntervention(true);
                          }}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
                          data-testid={`take-action-${idx}`}
                        >
                          Take Action
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500" data-testid="no-actions">
                No active priorities
              </div>
            )}
          </div>

          {/* RECOVERED VALUE */}
          <div className="bg-slate-800 rounded-2xl border border-slate-700/50 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
                Value Recovered
              </h2>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-emerald-400" data-testid="total-savings">
                  ${recovered_value?.total_savings?.toFixed(0) || "0"}
                </span>
                <span className="text-sm text-slate-400">total</span>
              </div>
            </div>
            
            {recovered_value?.recent_outcomes?.length > 0 ? (
              <div className="space-y-3" data-testid="verified-outcomes-list">
                {recovered_value.recent_outcomes.map((outcome, idx) => (
                  <div
                    key={outcome.outcome_id}
                    className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4"
                    data-testid={`outcome-${idx}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="font-medium text-white">
                          {outcome.asset_name}
                        </div>
                        <div className="text-xs text-slate-400">
                          {outcome.intervention_type}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold text-emerald-400">
                          +{outcome.savings_value?.toFixed(1)} {outcome.savings_unit}
                        </div>
                        <div className="text-xs text-slate-400">
                          {outcome.savings_type} savings
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className={`font-medium ${CONFIDENCE_COLORS[outcome.confidence_band]}`}>
                          {outcome.confidence_band}
                        </span>
                        <span className="text-slate-500">
                          {(outcome.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <div className="text-slate-500">
                        {outcome.time_to_verify_hours}h to verify
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500" data-testid="no-outcomes">
                No verified outcomes yet
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Intervention Modal */}
      {showIntervention && selectedAction && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setShowIntervention(false)}
        >
          <div
            className="bg-slate-800 rounded-2xl border border-slate-700 p-6 w-full max-w-md shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            data-testid="intervention-modal"
          >
            <h3 className="text-lg font-semibold mb-1">Create Intervention</h3>
            <p className="text-sm text-slate-400 mb-6">
              Taking action on {selectedAction.asset_name}
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1.5">
                  Intervention Type
                </label>
                <select
                  value={interventionForm.type}
                  onChange={(e) =>
                    setInterventionForm({ ...interventionForm, type: e.target.value })
                  }
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2.5 focus:border-emerald-500 outline-none"
                  data-testid="intervention-type-select"
                >
                  <option value="ADJUSTMENT">Adjustment</option>
                  <option value="CALIBRATION">Calibration</option>
                  <option value="REPAIR">Repair</option>
                  <option value="REPLACEMENT">Replacement</option>
                  <option value="MAINTENANCE">Maintenance</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-slate-400 mb-1.5">
                  Description
                </label>
                <textarea
                  value={interventionForm.description}
                  onChange={(e) =>
                    setInterventionForm({ ...interventionForm, description: e.target.value })
                  }
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2.5 h-24 focus:border-emerald-500 outline-none resize-none"
                  placeholder="Describe the action taken..."
                  data-testid="intervention-description"
                />
              </div>
              
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowIntervention(false)}
                  className="flex-1 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={createIntervention}
                  disabled={!interventionForm.description || loading}
                  className="flex-1 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors disabled:opacity-50"
                  data-testid="submit-intervention"
                >
                  Create Intervention
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800/80 backdrop-blur-sm border-t border-slate-700/50 px-6 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-500">
          <span>RAMP Command Centre</span>
          <span className="text-slate-600">
            Signal → State → Decision → Action → Learning
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
