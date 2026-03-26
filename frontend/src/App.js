import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import axios from "axios";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { useRAMPWebSocket, useRAMPPriorities } from "./hooks/useRAMPWebSocket";
import { ConnectionIndicator, ReconnectingBanner } from "./components/ConnectionStatus";
import { LoginForm, DemoCredentials } from "./components/LoginForm";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Band colors
const BAND_COLORS = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-500 text-white",
  MEDIUM: "bg-yellow-500 text-black",
  LOW: "bg-blue-500 text-white",
};

// Confidence label colors (labels: strong, moderate, low, insufficient)
const CONFIDENCE_LABEL_COLORS = {
  strong: "text-emerald-400",
  moderate: "text-yellow-400",
  low: "text-orange-400",
  insufficient: "text-red-400",
  unknown: "text-slate-400",
};

const INTEGRITY_COLORS = {
  HEALTHY: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  DEGRADED: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  POOR: "text-red-400 bg-red-500/10 border-red-500/20",
};

// Guided experience steps
const GUIDE_STEPS = [
  {
    id: "welcome",
    title: "Welcome to RAMP",
    subtitle: "Intelligent monitoring that learns from your operations",
    highlight: null,
  },
  {
    id: "site",
    title: "Your Facility",
    subtitle: "4 assets monitored with 14 days of baseline data",
    highlight: "site-context",
  },
  {
    id: "completed-loop",
    title: "Proven Results",
    subtitle: "One issue already detected, resolved, and verified",
    highlight: "completed-loop",
  },
  {
    id: "value-at-risk",
    title: "Current Value at Risk",
    subtitle: "Real-time visibility into where value is being lost",
    highlight: "value-at-risk",
  },
  {
    id: "actions",
    title: "Priority Actions",
    subtitle: "Ranked by impact, with clear explanations",
    highlight: "priority-actions",
  },
  {
    id: "continuous",
    title: "Continuous Monitoring",
    subtitle: "Not a one-off analysis — RAMP watches 24/7",
    highlight: "continuous",
  },
];

function App() {
  const [narrative, setNarrative] = useState(null);
  const [valueSummary, setValueSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [guideStep, setGuideStep] = useState(0);
  const [showGuide, setShowGuide] = useState(false);
  const [demoReady, setDemoReady] = useState(false);
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
    } catch (e) {
      console.error("Failed to fetch value summary", e);
    }
  }, []);

  // Start First 5 Minutes experience
  const startFirstFiveMinutes = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`${API}/system/demo/first-five-minutes`);
      setNarrative(res.data.narrative);
      setDemoReady(true);
      setShowGuide(true);
      setGuideStep(0);
      await fetchValueSummary();
    } catch (e) {
      setMessage({ type: "error", text: "Failed to initialize demo" });
    }
    setLoading(false);
  };

  // Create intervention
  const createIntervention = async () => {
    if (!selectedAction) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/how/interventions`, {
        state_id: selectedAction.state_id,
        intervention_type: interventionForm.type,
        description: interventionForm.description,
        created_by: "operator@riverside.com",
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

  // Guide navigation
  const nextStep = () => {
    if (guideStep < GUIDE_STEPS.length - 1) {
      setGuideStep(guideStep + 1);
    } else {
      setShowGuide(false);
    }
  };

  const prevStep = () => {
    if (guideStep > 0) {
      setGuideStep(guideStep - 1);
    }
  };

  const skipGuide = () => {
    setShowGuide(false);
  };

  // Initial load
  useEffect(() => {
    fetchValueSummary();
  }, [fetchValueSummary]);

  // Clear message
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const currentStep = GUIDE_STEPS[guideStep];
  const isHighlighted = (id) => showGuide && currentStep?.highlight === id;

  // Landing state - before demo starts
  if (!demoReady) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8">
        <div className="max-w-2xl text-center">
          <h1 className="text-4xl font-bold text-white mb-4">
            RAMP
          </h1>
          <p className="text-xl text-slate-300 mb-2">
            State-Based Industrial Intelligence
          </p>
          <p className="text-slate-400 mb-8 max-w-lg mx-auto">
            See where value is being lost, take action with confidence, and verify the results.
            All continuously, all automatically.
          </p>
          
          <button
            onClick={startFirstFiveMinutes}
            disabled={loading}
            className="px-8 py-4 bg-emerald-600 hover:bg-emerald-500 rounded-xl text-lg font-semibold transition-all transform hover:scale-105 disabled:opacity-50 disabled:transform-none"
            data-testid="start-demo-btn"
          >
            {loading ? "Initializing..." : "Start Demo"}
          </button>
          
          <p className="text-sm text-slate-500 mt-6">
            Takes about 5 minutes • No login required
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Guide Overlay */}
      {showGuide && (
        <div className="fixed inset-0 z-50 pointer-events-none">
          {/* Darkened background except highlighted area */}
          <div className="absolute inset-0 bg-black/60" />
          
          {/* Guide Card */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 pointer-events-auto">
            <div className="bg-slate-800 rounded-2xl border border-slate-600 p-6 w-[500px] shadow-2xl">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-emerald-400 font-medium uppercase tracking-wider">
                  Step {guideStep + 1} of {GUIDE_STEPS.length}
                </span>
                <button
                  onClick={skipGuide}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Skip tour
                </button>
              </div>
              <h3 className="text-xl font-semibold text-white mb-1">
                {currentStep?.title}
              </h3>
              <p className="text-slate-300 mb-4">
                {currentStep?.subtitle}
              </p>
              
              {/* Step-specific content */}
              {currentStep?.id === "welcome" && (
                <p className="text-sm text-slate-400 mb-4">
                  Let's walk through what RAMP can do for your operations.
                </p>
              )}
              {currentStep?.id === "completed-loop" && narrative?.completed_loop && (
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 mb-4">
                  <p className="text-sm text-emerald-300">
                    <strong>{narrative.completed_loop.asset}:</strong> {narrative.completed_loop.issue} → {narrative.completed_loop.outcome}
                  </p>
                </div>
              )}
              {currentStep?.id === "continuous" && (
                <p className="text-sm text-slate-400 mb-4">
                  RAMP learns from every intervention to improve detection and recommendations.
                </p>
              )}
              
              <div className="flex items-center justify-between">
                <div className="flex gap-1">
                  {GUIDE_STEPS.map((_, idx) => (
                    <div
                      key={idx}
                      className={`w-2 h-2 rounded-full ${
                        idx === guideStep ? "bg-emerald-400" : "bg-slate-600"
                      }`}
                    />
                  ))}
                </div>
                <div className="flex gap-2">
                  {guideStep > 0 && (
                    <button
                      onClick={prevStep}
                      className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                    >
                      Back
                    </button>
                  )}
                  <button
                    onClick={nextStep}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium"
                    data-testid="guide-next-btn"
                  >
                    {guideStep === GUIDE_STEPS.length - 1 ? "Get Started" : "Continue"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold tracking-tight">
                RAMP <span className="text-slate-400 font-normal">Command Centre</span>
              </h1>
              {valueSummary?.loop_integrity && (
                <span
                  className={`text-xs px-2.5 py-1 rounded-full border ${INTEGRITY_COLORS[valueSummary.loop_integrity.status]}`}
                  data-testid="loop-status"
                >
                  {valueSummary.loop_integrity.status}
                </span>
              )}
            </div>
            {!showGuide && (
              <button
                onClick={() => { setShowGuide(true); setGuideStep(0); }}
                className="text-sm text-slate-400 hover:text-white"
              >
                Replay tour
              </button>
            )}
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
      <main className="max-w-7xl mx-auto px-6 py-8 pb-24">
        {/* Site Context */}
        <div 
          className={`mb-6 p-4 rounded-xl bg-slate-800/50 border transition-all duration-300 ${
            isHighlighted("site-context") 
              ? "border-emerald-500 ring-2 ring-emerald-500/30 relative z-[60]" 
              : "border-slate-700/50"
          }`}
          data-testid="site-context"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-white">
                {narrative?.site?.name || "Loading..."}
              </h2>
              <p className="text-sm text-slate-400">
                {narrative?.site?.assets_monitored || 0} assets monitored • {narrative?.site?.baseline_data_days || 14} days baseline data
              </p>
            </div>
            <div className="flex gap-2">
              {narrative?.site?.systems?.map((system, idx) => (
                <span key={idx} className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                  {system}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Top Row: Completed Loop + Value at Risk */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* COMPLETED LOOP - Proof */}
          <div 
            className={`bg-emerald-500/5 rounded-2xl border p-5 transition-all duration-300 ${
              isHighlighted("completed-loop") 
                ? "border-emerald-500 ring-2 ring-emerald-500/30 relative z-[60]" 
                : "border-emerald-500/20"
            }`}
            data-testid="completed-loop"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <h3 className="text-sm font-medium text-emerald-400 uppercase tracking-wider">
                Completed Loop
              </h3>
            </div>
            
            {narrative?.completed_loop ? (
              <>
                <div className="text-white font-medium mb-1">
                  {narrative.completed_loop.asset}
                </div>
                <div className="text-sm text-slate-400 mb-3">
                  {narrative.completed_loop.issue}
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <span className="text-slate-500 mt-0.5">→</span>
                    <span className="text-slate-300">{narrative.completed_loop.action}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-emerald-400 mt-0.5">✓</span>
                    <span className="text-emerald-300">{narrative.completed_loop.outcome}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-slate-500">Loading...</div>
            )}
          </div>

          {/* VALUE AT RISK - Hero */}
          <div 
            className={`col-span-2 bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-2xl border p-6 transition-all duration-300 ${
              isHighlighted("value-at-risk") 
                ? "border-emerald-500 ring-2 ring-emerald-500/30 relative z-[60]" 
                : "border-slate-700/50"
            }`}
            data-testid="value-at-risk"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-1">
                  Current Value at Risk
                </h2>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold text-amber-400" data-testid="total-var">
                    ${narrative?.current_value_at_risk?.total_per_day?.toLocaleString() || valueSummary?.value_at_risk?.total_per_day?.toLocaleString() || "0"}
                  </span>
                  <span className="text-xl text-slate-400">/day</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold text-emerald-400">
                  {valueSummary?.loop_integrity?.verification_rate_percent || 100}%
                </div>
                <div className="text-xs text-slate-400">verification rate</div>
              </div>
            </div>
            
            {/* VaR Breakdown */}
            <div className="flex gap-4">
              {narrative?.current_value_at_risk?.breakdown?.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[item.band]}`}>
                    {item.band}
                  </span>
                  <span className="text-sm text-slate-300">${item.var?.toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Priority Actions */}
        <div 
          className={`bg-slate-800 rounded-2xl border p-6 mb-6 transition-all duration-300 ${
            isHighlighted("priority-actions") 
              ? "border-emerald-500 ring-2 ring-emerald-500/30 relative z-[60]" 
              : "border-slate-700/50"
          }`}
          data-testid="priority-actions"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
              Priority Actions
            </h2>
            <span className="text-xs text-slate-500">
              Ranked by impact • Click to take action
            </span>
          </div>
          
          <div className="space-y-3" data-testid="actions-list">
            {narrative?.priority_actions?.map((action, idx) => (
              <div
                key={idx}
                className="bg-slate-700/30 rounded-xl p-4 border border-slate-700/50 hover:border-slate-500 transition-colors cursor-pointer group"
                onClick={() => {
                  setSelectedAction(action);
                  setShowIntervention(true);
                }}
                data-testid={`action-${idx}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-bold text-slate-600">#{action.rank}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[action.band]}`}>
                          {action.band}
                        </span>
                        <span className="font-medium text-white">{action.asset}</span>
                      </div>
                      <div className="text-sm text-slate-400 mt-0.5">{action.issue}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-semibold text-amber-400">
                      ${action.var_per_day?.toFixed(0)}
                      <span className="text-xs text-slate-400">/day</span>
                    </div>
                    <div className={`text-xs capitalize ${CONFIDENCE_LABEL_COLORS[action.confidence_label] || CONFIDENCE_LABEL_COLORS.unknown}`}>
                      {action.confidence_label} confidence
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="text-sm text-slate-500 italic">
                    → {action.recommended_action}
                  </div>
                  <button
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedAction(action);
                      setShowIntervention(true);
                    }}
                    data-testid={`take-action-${idx}`}
                  >
                    Take Action
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Continuous Monitoring */}
        <div 
          className={`bg-slate-800/50 rounded-2xl border p-6 transition-all duration-300 ${
            isHighlighted("continuous") 
              ? "border-emerald-500 ring-2 ring-emerald-500/30 relative z-[60]" 
              : "border-slate-700/50"
          }`}
          data-testid="continuous"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
              <div>
                <div className="text-white font-medium">Continuous Monitoring Active</div>
                <div className="text-sm text-slate-400">
                  {narrative?.continuous_monitoring?.assets_healthy || 0} healthy • {narrative?.continuous_monitoring?.assets_in_state || 0} in active state • Learning enabled
                </div>
              </div>
            </div>
            <div className="text-xs text-slate-500">
              Signal → State → Decision → Action → Learning
            </div>
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
            <p className="text-sm text-slate-400 mb-4">
              {selectedAction.asset}: {selectedAction.issue}
            </p>
            
            <div className="bg-slate-700/50 rounded-lg p-3 mb-4">
              <div className="text-xs text-slate-400 mb-1">Recommended</div>
              <div className="text-sm text-white">{selectedAction.recommended_action}</div>
            </div>
            
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
                  What did you do?
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
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800/80 backdrop-blur-sm border-t border-slate-700/50 px-6 py-2 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-500">
          <span>RAMP Command Centre</span>
          <span className="text-slate-600">
            Continuously learning from your operations
          </span>
        </div>
      </footer>
    </div>
  );
}

/**
 * AppContent - The main authenticated content
 */
function AppContent() {
  const { isAuthenticated, token, user, signOut, canAccessHOW } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  
  // WebSocket connection - only connect if authenticated and has HOW access
  const { 
    isConnected, 
    priorities: wsPriorities,
    priorityDistribution,
    totalValueAtRisk: wsValueAtRisk,
    connect: wsConnect,
  } = useRAMPWebSocket(canAccessHOW ? token : null, { 
    autoConnect: canAccessHOW 
  });

  // If not authenticated, show login option
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-8">
        <div className="max-w-md w-full">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-white mb-4">
              RAMP
            </h1>
            <p className="text-xl text-slate-300 mb-2">
              State-Based Industrial Intelligence
            </p>
            <p className="text-slate-400">
              Sign in to access real-time monitoring
            </p>
          </div>
          
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6">
            <LoginForm 
              initialEmail={loginEmail}
              initialPassword={loginPassword}
            />
            
            <div className="mt-6 pt-6 border-t border-slate-700">
              <DemoCredentials 
                onSelect={(email, password) => {
                  setLoginEmail(email);
                  setLoginPassword(password);
                }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Authenticated - show main app with WebSocket integration
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold tracking-tight">
                RAMP <span className="text-slate-400 font-normal">Command Centre</span>
              </h1>
              <ConnectionIndicator />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-slate-400">
                {user?.email}
                <span className="ml-2 px-2 py-0.5 bg-slate-700 rounded text-xs capitalize">
                  {user?.role}
                </span>
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

      {/* Reconnecting Banner */}
      <ReconnectingBanner className="mx-6 mt-4" />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 pb-24">
        {/* Real-time Value Summary */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-2xl border border-slate-700/50 p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-1">
                Live Value at Risk
              </h2>
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-bold text-amber-400" data-testid="live-var">
                  ${wsValueAtRisk?.toLocaleString() || "0"}
                </span>
                <span className="text-xl text-slate-400">/day</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-semibold text-white">
                {wsPriorities?.length || 0}
              </div>
              <div className="text-xs text-slate-400">active priorities</div>
            </div>
          </div>
          
          {/* Priority Distribution */}
          <div className="flex gap-4">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(band => (
              <div key={band} className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${BAND_COLORS[band]}`}>
                  {band}
                </span>
                <span className="text-sm text-slate-300">
                  {priorityDistribution?.[band] || 0}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Real-time Priority List */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700/50 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
              Live Priority Queue
              {isConnected && (
                <span className="ml-2 text-emerald-400 text-xs">
                  (real-time)
                </span>
              )}
            </h2>
            <span className="text-xs text-slate-500">
              Updates automatically via WebSocket
            </span>
          </div>
          
          <div className="space-y-3" data-testid="live-priorities">
            {wsPriorities?.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                {isConnected ? 'No active priorities' : 'Connecting to live updates...'}
              </div>
            ) : (
              wsPriorities?.map((priority, idx) => (
                <div
                  key={priority.priority_id || priority.id || idx}
                  className="bg-slate-700/30 rounded-xl p-4 border border-slate-700/50"
                  data-testid={`live-priority-${idx}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-slate-600">#{idx + 1}</span>
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
                          {priority.state_type || 'Active state'}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-semibold text-amber-400">
                        ${(priority.value_at_risk_per_day || priority.economic_impact?.value_at_risk_per_day || 0).toFixed(0)}
                        <span className="text-xs text-slate-400">/day</span>
                      </div>
                      <div className="text-xs text-slate-500">
                        Score: {priority.priority_score || 0}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800/80 backdrop-blur-sm border-t border-slate-700/50 px-6 py-2 z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-slate-500">
          <span>RAMP Command Centre</span>
          <ConnectionIndicator showLabel={true} />
        </div>
      </footer>
    </div>
  );
}

/**
 * Root App with Providers
 */
function AppWithProviders() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

// Keep the original App for demo mode
export { App as DemoApp };
export default AppWithProviders;
