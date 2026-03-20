import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Priority band colors
const BAND_COLORS = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-black",
  LOW: "bg-blue-500 text-white",
};

const BAND_BG = {
  CRITICAL: "border-red-600 bg-red-50",
  HIGH: "border-orange-500 bg-orange-50",
  MEDIUM: "border-yellow-500 bg-yellow-50",
  LOW: "border-blue-500 bg-blue-50",
};

// Severity band colors
const SEVERITY_COLORS = {
  CRITICAL: "text-red-600",
  HIGH: "text-orange-500",
  MEDIUM: "text-yellow-600",
  LOW: "text-blue-500",
};

function App() {
  const [view, setView] = useState("how"); // "how" or "where"
  const [priorities, setPriorities] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [assetState, setAssetState] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showIntervention, setShowIntervention] = useState(false);
  const [interventionForm, setInterventionForm] = useState({
    type: "adjustment",
    description: "",
  });
  const [message, setMessage] = useState(null);

  // Fetch system health
  const fetchHealth = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/system/health`);
      setSystemHealth(res.data);
    } catch (e) {
      console.error("Health check failed", e);
    }
  }, []);

  // Fetch HOW priorities
  const fetchPriorities = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/how/priorities`);
      setPriorities(res.data.priorities || []);
    } catch (e) {
      console.error("Failed to fetch priorities", e);
    }
  }, []);

  // Fetch WHERE summary
  const fetchPortfolioSummary = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/where/priorities/summary`);
      setPortfolioSummary(res.data);
    } catch (e) {
      console.error("Failed to fetch portfolio summary", e);
    }
  }, []);

  // Fetch asset state
  const fetchAssetState = useCallback(async (assetId) => {
    try {
      const res = await axios.get(`${API}/how/assets/${assetId}/state`);
      setAssetState(res.data);
    } catch (e) {
      console.error("Failed to fetch asset state", e);
    }
  }, []);

  // Seed demo data
  const seedData = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/system/seed`);
      setMessage({ type: "success", text: "Demo data seeded successfully" });
    } catch (e) {
      setMessage({ type: "error", text: "Failed to seed data" });
    }
    setLoading(false);
  };

  // Simulate drift
  const simulateDrift = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/system/demo/simulate-drift`);
      setMessage({
        type: "success",
        text: `Simulated drift: ${res.data.active_states} active states, ${res.data.active_priorities} priorities`,
      });
      await fetchPriorities();
      await fetchPortfolioSummary();
    } catch (e) {
      setMessage({ type: "error", text: "Failed to simulate drift" });
    }
    setLoading(false);
  };

  // Create intervention
  const createIntervention = async (stateId) => {
    setLoading(true);
    try {
      await axios.post(`${API}/how/interventions`, {
        state_id: stateId,
        intervention_type: interventionForm.type,
        description: interventionForm.description,
        created_by: "operator-001",
      });
      setMessage({
        type: "success",
        text: "Intervention created. Baseline frozen for verification.",
      });
      setShowIntervention(false);
      setInterventionForm({ type: "adjustment", description: "" });
      await fetchPriorities();
    } catch (e) {
      setMessage({ type: "error", text: "Failed to create intervention" });
    }
    setLoading(false);
  };

  // Initial load
  useEffect(() => {
    fetchHealth();
    fetchPriorities();
    fetchPortfolioSummary();
    
    // Poll for updates every 30 seconds
    const interval = setInterval(() => {
      fetchPriorities();
      fetchPortfolioSummary();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [fetchHealth, fetchPriorities, fetchPortfolioSummary]);

  // Clear message after 3 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight">
              RAMP <span className="text-slate-400 font-normal">Command Centre</span>
            </h1>
            {systemHealth && (
              <span
                className={`text-xs px-2 py-1 rounded ${
                  systemHealth.ramp_initialized
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-red-500/20 text-red-400"
                }`}
                data-testid="system-status"
              >
                {systemHealth.ramp_initialized ? "ONLINE" : "OFFLINE"}
              </span>
            )}
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-2 bg-slate-700/50 rounded-lg p-1">
            <button
              onClick={() => setView("how")}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-all ${
                view === "how"
                  ? "bg-slate-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              data-testid="how-lens-btn"
            >
              HOW Lens
            </button>
            <button
              onClick={() => setView("where")}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-all ${
                view === "where"
                  ? "bg-slate-600 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
              data-testid="where-lens-btn"
            >
              WHERE Lens
            </button>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={seedData}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 rounded transition-colors"
              data-testid="seed-data-btn"
            >
              Seed Data
            </button>
            <button
              onClick={simulateDrift}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-500 rounded transition-colors"
              data-testid="simulate-drift-btn"
            >
              Simulate Drift
            </button>
          </div>
        </div>
      </header>

      {/* Message Toast */}
      {message && (
        <div
          className={`fixed top-20 right-6 px-4 py-2 rounded shadow-lg z-50 ${
            message.type === "success" ? "bg-emerald-600" : "bg-red-600"
          }`}
          data-testid="message-toast"
        >
          {message.text}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {view === "how" ? (
          /* HOW LENS VIEW */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium">Priority Queue</h2>
              <span className="text-sm text-slate-400">
                {priorities.length} active priorities
              </span>
            </div>

            {/* Priority Cards */}
            {priorities.length === 0 ? (
              <div className="text-center py-12 text-slate-500" data-testid="no-priorities">
                No active priorities. Click "Simulate Drift" to create a demo scenario.
              </div>
            ) : (
              <div className="grid gap-4" data-testid="priority-list">
                {priorities.map((priority) => (
                  <div
                    key={priority.priority_id}
                    className={`border-l-4 rounded-lg bg-slate-800 p-4 ${
                      BAND_BG[priority.priority_band] || "border-slate-600"
                    }`}
                    data-testid={`priority-card-${priority.priority_id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-semibold ${
                              BAND_COLORS[priority.priority_band] || "bg-slate-600"
                            }`}
                          >
                            {priority.priority_band}
                          </span>
                          <span className="text-xs text-slate-400 uppercase">
                            {priority.priority_type}
                          </span>
                        </div>
                        <h3 className="font-medium text-white mb-1">
                          {priority.asset_name}
                        </h3>
                        <div className="space-y-1">
                          {priority.drivers.map((driver, i) => (
                            <p key={i} className="text-sm text-slate-300">
                              • {driver}
                            </p>
                          ))}
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-lg font-semibold text-amber-400">
                          ${priority.value_at_risk_per_day.toFixed(0)}
                          <span className="text-xs text-slate-400">/day</span>
                        </div>
                        <div className="text-xs text-slate-400">at risk</div>
                        <button
                          onClick={() => {
                            setSelectedAsset(priority.asset_id);
                            fetchAssetState(priority.asset_id);
                          }}
                          className="mt-2 px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded"
                          data-testid={`view-asset-${priority.asset_id}`}
                        >
                          View Asset
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Asset State Panel */}
            {assetState && (
              <div className="mt-6 bg-slate-800 rounded-lg p-4" data-testid="asset-state-panel">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium">
                    {assetState.asset_name}
                    <span className="ml-2 text-xs text-slate-400">
                      Criticality: {assetState.criticality_band}
                    </span>
                  </h3>
                  <button
                    onClick={() => {
                      setAssetState(null);
                      setSelectedAsset(null);
                    }}
                    className="text-slate-400 hover:text-white"
                  >
                    ×
                  </button>
                </div>

                {/* Active States */}
                {assetState.active_states.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-slate-400 mb-2">
                      Active States
                    </h4>
                    {assetState.active_states.map((state) => (
                      <div
                        key={state.state_id}
                        className="flex items-center justify-between bg-slate-700/50 rounded p-3 mb-2"
                      >
                        <div>
                          <span className="font-medium">{state.state_type}</span>
                          <span className="ml-2 text-xs text-slate-400">
                            {state.state_family}
                          </span>
                          <div className="text-sm text-slate-300">
                            {state.deviation_percent?.toFixed(1)}% deviation •{" "}
                            <span
                              className={SEVERITY_COLORS[state.severity_band]}
                            >
                              {state.severity_band}
                            </span>{" "}
                            severity •{" "}
                            <span className="text-slate-400">
                              {state.confidence_band} confidence
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => {
                            setShowIntervention(true);
                          }}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm"
                          data-testid={`intervene-btn-${state.state_id}`}
                        >
                          Take Action
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Intervention Modal */}
                {showIntervention && assetState.active_states[0] && (
                  <div
                    className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                    onClick={() => setShowIntervention(false)}
                  >
                    <div
                      className="bg-slate-800 rounded-lg p-6 w-full max-w-md"
                      onClick={(e) => e.stopPropagation()}
                      data-testid="intervention-modal"
                    >
                      <h3 className="text-lg font-medium mb-4">
                        Create Intervention
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm text-slate-400 mb-1">
                            Intervention Type
                          </label>
                          <select
                            value={interventionForm.type}
                            onChange={(e) =>
                              setInterventionForm({
                                ...interventionForm,
                                type: e.target.value,
                              })
                            }
                            className="w-full bg-slate-700 rounded px-3 py-2"
                            data-testid="intervention-type-select"
                          >
                            <option value="adjustment">Adjustment</option>
                            <option value="repair">Repair</option>
                            <option value="replacement">Replacement</option>
                            <option value="investigation">Investigation</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm text-slate-400 mb-1">
                            Description
                          </label>
                          <textarea
                            value={interventionForm.description}
                            onChange={(e) =>
                              setInterventionForm({
                                ...interventionForm,
                                description: e.target.value,
                              })
                            }
                            className="w-full bg-slate-700 rounded px-3 py-2 h-24"
                            placeholder="Describe the action taken..."
                            data-testid="intervention-description-input"
                          />
                        </div>
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={() => setShowIntervention(false)}
                            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() =>
                              createIntervention(
                                assetState.active_states[0].state_id
                              )
                            }
                            disabled={!interventionForm.description}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded disabled:opacity-50"
                            data-testid="submit-intervention-btn"
                          >
                            Create Intervention
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* WHERE LENS VIEW */
          <div className="space-y-6">
            <h2 className="text-lg font-medium">Portfolio Overview</h2>

            {portfolioSummary ? (
              <div className="space-y-6" data-testid="portfolio-summary">
                {/* Summary Cards */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-slate-800 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">
                      Active Priorities
                    </div>
                    <div className="text-2xl font-semibold">
                      {portfolioSummary.total_active}
                    </div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">
                      Value at Risk
                    </div>
                    <div className="text-2xl font-semibold text-amber-400">
                      ${portfolioSummary.total_value_at_risk_per_day.toFixed(0)}
                      <span className="text-sm text-slate-400">/day</span>
                    </div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">
                      Value Recoverable
                    </div>
                    <div className="text-2xl font-semibold text-emerald-400">
                      ${portfolioSummary.total_value_recoverable_per_day.toFixed(0)}
                      <span className="text-sm text-slate-400">/day</span>
                    </div>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">Currency</div>
                    <div className="text-2xl font-semibold">
                      {portfolioSummary.currency}
                    </div>
                  </div>
                </div>

                {/* Priority Distribution */}
                <div className="bg-slate-800 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-slate-400 mb-4">
                    Priority Distribution
                  </h3>
                  <div className="flex items-end gap-2 h-32">
                    {Object.entries(portfolioSummary.distribution).map(
                      ([band, count]) => (
                        <div key={band} className="flex-1 flex flex-col items-center">
                          <div
                            className={`w-full rounded-t ${
                              BAND_COLORS[band] || "bg-slate-600"
                            }`}
                            style={{
                              height: `${Math.max(
                                (count / Math.max(portfolioSummary.total_active, 1)) * 100,
                                count > 0 ? 10 : 0
                              )}%`,
                            }}
                          />
                          <div className="mt-2 text-xs text-slate-400">
                            {band}
                          </div>
                          <div className="text-sm font-medium">{count}</div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                Loading portfolio data...
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 px-6 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-400">
          <span>RAMP Command Centre v{systemHealth?.version || "0.1.0"}</span>
          <span>
            Signal → State → Decision → Action → Learning
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
