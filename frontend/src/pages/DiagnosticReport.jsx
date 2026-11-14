import { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import PrerequisiteGraph from '../components/PrerequisiteGraph';
import { 
  Brain, 
  AlertCircle, 
  CheckCircle2, 
  BarChart3, 
  ArrowLeft,
  TrendingDown,
  Info,
  Clock,
  Compass,
  Milestone,
  Zap,
  ShieldAlert,
  Sparkles,
  Layers,
  ArrowRight,
  Bot,
  Play,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

export default function DiagnosticReport() {
  const { user } = useAuth();
  const { studentId: routeStudentId } = useParams();
  const navigate = useNavigate();
  const isTeacherView = user?.role === 'teacher' && Boolean(routeStudentId);
  const targetStudentId = routeStudentId ? Number(routeStudentId) : user?.id;

  const [activeTab, setActiveTab] = useState('roadmap'); // 'roadmap', 'quadrants', 'dina'
  const [report, setReport] = useState([]);
  const [masteryData, setMasteryData] = useState([]);
  const [advancedData, setAdvancedData] = useState(null);
  const [conceptGraph, setConceptGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Agentic AI Tutor State (Draft & Preview)
  const [agentDraft, setAgentDraft] = useState(null);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentApproving, setAgentApproving] = useState(false);
  const [agentNotice, setAgentNotice] = useState(null);
  const [agentError, setAgentError] = useState(null);
  const [showTrace, setShowTrace] = useState(true);

  const fetchData = async () => {
    if (!targetStudentId) {
      setError("Invalid user session. Please log out and log in again.");
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      const [reportRes, masteryRes, advRes, graphRes] = await Promise.all([
        api.get(`/diagnosis/student/${targetStudentId}/report`),
        api.get(`/diagnosis/student/${targetStudentId}`),
        api.get(`/diagnosis/student/${targetStudentId}/advanced-analytics`).catch(err => {
          console.warn("Advanced analytics fallback:", err);
          return { data: null };
        }),
        api.get('/concepts/graph').catch(() => ({ data: { nodes: [], edges: [] } }))
      ]);
      setReport(reportRes.data);
      setMasteryData(masteryRes.data);
      setAdvancedData(advRes.data);
      setConceptGraph(graphRes.data || { nodes: [], edges: [] });
      setError(null);
    } catch (err) {
      console.error("Failed to fetch diagnostic data:", err);
      setError("Failed to load diagnostic report. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadDiagnostic = async () => {
      if (!user) return;
      if (!targetStudentId) {
        await Promise.resolve();
        setError("Invalid user session. Please log out and log in again.");
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        const [reportRes, masteryRes, advRes, graphRes] = await Promise.all([
          api.get(`/diagnosis/student/${targetStudentId}/report`),
          api.get(`/diagnosis/student/${targetStudentId}`),
          api.get(`/diagnosis/student/${targetStudentId}/advanced-analytics`).catch(err => {
            console.warn("Advanced analytics fallback:", err);
            return { data: null };
          }),
          api.get('/concepts/graph').catch(() => ({ data: { nodes: [], edges: [] } }))
        ]);
        setReport(reportRes.data);
        setMasteryData(masteryRes.data);
        setAdvancedData(advRes.data);
        setConceptGraph(graphRes.data || { nodes: [], edges: [] });
        setError(null);
      } catch (err) {
        console.error("Failed to fetch diagnostic data:", err);
        setError("Failed to load diagnostic report. Please try again later.");
      } finally {
        setLoading(false);
      }
    };
    loadDiagnostic();
  }, [user, targetStudentId]);

  const getReliabilityColor = (tier) => {
    switch (tier) {
      case 'HIGH': return 'text-emerald-600 bg-emerald-50 border-emerald-100';
      case 'MEDIUM': return 'text-amber-600 bg-amber-50 border-amber-100';
      case 'LOW': return 'text-slate-500 bg-slate-50 border-slate-100';
      default: return 'text-slate-500 bg-slate-50 border-slate-100';
    }
  };

  const getMasteryColor = (mastery) => {
    if (mastery >= 0.70) return 'bg-emerald-500';
    if (mastery >= 0.40) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  const runTutorAgent = async (targetConceptId = null) => {
    if (!targetStudentId) return;
    try {
      setAgentLoading(true);
      setAgentError(null);
      setAgentNotice(null);
      const { data } = await api.post(`/agent/student/${targetStudentId}/diagnose-draft`, {
        target_concept_id: targetConceptId,
        max_questions: 4
      });
      setAgentDraft(data);
      setShowTrace(true);
    } catch (err) {
      console.error("Failed to run AI Tutor Agent:", err);
      setAgentError(err.response?.data?.detail || "Failed to run AI Tutor Agent.");
    } finally {
      setAgentLoading(false);
    }
  };

  const approveAndStartQuiz = async () => {
    if (!agentDraft || !targetStudentId) return;
    try {
      setAgentApproving(true);
      setAgentError(null);
      setAgentNotice(null);
      const { data } = await api.post(`/agent/student/${targetStudentId}/approve-quiz`, {
        title: agentDraft.draft_quiz_title,
        questions: agentDraft.draft_questions
      });
      if (isTeacherView) {
        setAgentNotice(`Assigned "${data.title}" (${data.question_count} questions) to Student #${targetStudentId}.`);
      } else {
        navigate(`/student/take-test/${data.test_id}`);
      }
    } catch (err) {
      console.error("Failed to approve remedial quiz:", err);
      setAgentError(err.response?.data?.detail || "Failed to launch approved quiz.");
    } finally {
      setAgentApproving(false);
    }
  };

  const studentGraphData = useMemo(() => {
    const masteryById = new Map();
    (masteryData || []).forEach(m => {
      masteryById.set(String(m.concept_id), m.adjusted_mastery);
    });
    const roadmapList = advancedData?.prerequisite_debt_report?.remediation_roadmap || [];
    const rootBlockerIds = new Set(
      roadmapList
        .filter(item => item.is_root_blocker)
        .map(item => String(item.concept_id))
    );

    const nodes = (conceptGraph?.nodes || []).map(n => {
      const id = String(n.id);
      return {
        id,
        conceptId: n.id,
        label: n.name,
        mastery: masteryById.has(id) ? masteryById.get(id) : null,
        isRootBlocker: rootBlockerIds.has(id),
      };
    });

    const edges = (conceptGraph?.edges || []).map(e => ({
      id: `edge-${e.id}`,
      from: String(e.from_concept_id),
      to: String(e.to_concept_id),
      confidence: e.confidence ?? 0.85,
      reasoning: e.source ? `Source: ${e.source}` : '',
    }));

    return { nodes, edges };
  }, [conceptGraph, masteryData, advancedData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p className="text-slate-500 animate-pulse font-medium">Computing Multi-Model Psychometric Diagnosis & Learning Roadmap...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto mt-12 p-8 glass-panel text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-slate-900 mb-2">Oops! Something went wrong</h2>
        <p className="text-slate-600 mb-6">{error}</p>
        <button 
          onClick={fetchData}
          className="bg-indigo-600 text-white px-6 py-2 rounded-xl hover:bg-indigo-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  const roadmapData = advancedData?.prerequisite_debt_report;
  const quadrantData = advancedData?.quadrant_distribution;
  const execSummary = advancedData?.executive_summary;

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <button 
            onClick={() => navigate(isTeacherView ? -1 : '/student')}
            className="flex items-center text-slate-500 hover:text-indigo-600 mb-2 transition-colors group text-sm font-semibold"
          >
            <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
            {isTeacherView ? 'Back to Class Results' : 'Back to Dashboard'}
          </button>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight flex items-center gap-3">
              <Brain className="w-10 h-10 text-indigo-600" />
              {isTeacherView ? `Student #${targetStudentId} Diagnostic Dossier` : 'Cognitive Diagnostic Dossier'}
            </h1>
            <span className="px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-indigo-100 text-indigo-700 border border-indigo-200">
              Tri-Model AI Active
            </span>
          </div>
          <p className="text-slate-500 mt-2 text-base">
            Multi-Attribute DINA diagnosis, Bayesian knowledge tracing, and response-time effort analytics.
          </p>
        </div>
      </div>

      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 border-l-4 border-indigo-500 bg-white/80 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Concept Mastery</span>
            <BarChart3 className="w-5 h-5 text-indigo-600" />
          </div>
          <p className="text-3xl font-black text-slate-900">
            {Math.round(masteryData.reduce((acc, curr) => acc + curr.adjusted_mastery, 0) / (masteryData.length || 1) * 100)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">Across {masteryData.length} syllabus concepts</p>
        </div>

        <div className="glass-panel p-5 border-l-4 border-rose-500 bg-white/80 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Prerequisite Debt</span>
            <ShieldAlert className="w-5 h-5 text-rose-600" />
          </div>
          <p className="text-3xl font-black text-slate-900">
            {execSummary ? Math.round(execSummary.prerequisite_debt_score * 100) : 0}%
          </p>
          <p className="text-xs text-rose-600 font-semibold mt-1">
            {execSummary?.debt_level?.replace(/_/g, ' ') || 'Normal'}
          </p>
        </div>

        <div className="glass-panel p-5 border-l-4 border-emerald-500 bg-white/80 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Cognitive Effort</span>
            <Zap className="w-5 h-5 text-emerald-600" />
          </div>
          <p className="text-3xl font-black text-slate-900">
            {execSummary ? Math.round(execSummary.effort_consistency_index * 100) : 100}%
          </p>
          <p className="text-xs text-emerald-600 font-semibold mt-1">Effort Consistency Index</p>
        </div>

        <div className="glass-panel p-5 border-l-4 border-amber-500 bg-white/80 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Critical Gaps</span>
            <TrendingDown className="w-5 h-5 text-amber-600" />
          </div>
          <p className="text-3xl font-black text-slate-900">
            {masteryData.filter(m => m.adjusted_mastery < 0.50).length}
          </p>
          <p className="text-xs text-slate-500 mt-1">Concepts needing targeted practice</p>
        </div>
      </div>

      {/* Agentic AI Cognitive Tutor Panel (Draft & Preview + Reasoning Trace) */}
      <div className="glass-panel p-6 border border-indigo-200 bg-gradient-to-br from-indigo-50/80 via-white to-slate-50 rounded-2xl shadow-sm space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-3 rounded-xl bg-indigo-600 text-white shadow-xs">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-black text-slate-900">AI Cognitive Tutor Agent</h2>
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-indigo-100 text-indigo-700 border border-indigo-200">
                  Neuro-Symbolic ReAct Brain
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-1">
                Autonomously inspects your DINA mastery, BKT trajectory, response-time effort, chosen distractors, and Prerequisite DAG to draft a personalized remedial check.
              </p>
            </div>
          </div>

          <button
            onClick={() => runTutorAgent(null)}
            disabled={agentLoading}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold shadow-xs transition-colors flex items-center gap-2 disabled:opacity-60 self-start md:self-auto"
          >
            <Sparkles className="w-4 h-4" />
            {agentLoading ? 'Reasoning Over Models...' : agentDraft ? 'Re-Run AI Tutor Agent' : 'Run AI Tutor Agent'}
          </button>
        </div>

        {agentError && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
            {agentError}
          </div>
        )}

        {agentNotice && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            {agentNotice}
          </div>
        )}

        {agentDraft && (
          <div className="space-y-5 pt-3 border-t border-indigo-100">
            {/* Engine Mode + Strategy Verdict */}
            <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="px-3 py-1 rounded-lg text-xs font-black uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200">
                  Strategy: {agentDraft.strategy_code.replace(/_/g, ' ')}
                </span>
                <span className="px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold bg-slate-100 text-slate-700">
                  Brain Engine: {agentDraft.engine_mode}
                </span>
              </div>
              <p className="text-sm text-slate-800 leading-relaxed font-medium">
                {agentDraft.diagnosis_summary}
              </p>

              {agentDraft.distractor_insights?.length > 0 && (
                <div className="p-3 rounded-xl bg-rose-50/60 border border-rose-100 space-y-1">
                  <p className="text-[11px] font-black uppercase tracking-wider text-rose-700">
                    Distractor Misconception Analysis
                  </p>
                  <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                    {agentDraft.distractor_insights.map((ins, i) => (
                      <li key={i}>{ins}</li>
                    ))}
                  </ul>
                </div>
              )}

              {agentDraft.study_coaching?.length > 0 && (
                <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-100 space-y-1">
                  <p className="text-[11px] font-black uppercase tracking-wider text-emerald-700">
                    Prescriptive Coaching Steps
                  </p>
                  <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                    {agentDraft.study_coaching.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Collapsible Live Reasoning Trace */}
            <div className="rounded-xl border border-slate-200 bg-slate-900 text-slate-100 overflow-hidden">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="w-full px-4 py-3 flex items-center justify-between text-left bg-slate-800/80 hover:bg-slate-800 transition-colors"
              >
                <span className="text-xs font-black uppercase tracking-wider text-indigo-300 flex items-center gap-2">
                  <Brain className="w-4 h-4" />
                  Live Reasoning Trace ({agentDraft.reasoning_trace?.length || 0} Steps: Thought → Tool → Observation)
                </span>
                {showTrace ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
              </button>
              {showTrace && (
                <div className="p-4 space-y-3 text-xs font-mono">
                  {agentDraft.reasoning_trace?.map((st) => (
                    <div key={st.step} className="p-3 rounded-lg bg-slate-800/60 border border-slate-700 space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-amber-300 font-bold">
                          Step {st.step} • Tool: {st.tool_name}
                        </span>
                        <span className="text-slate-400">[{st.provider}]</span>
                      </div>
                      <p className="text-slate-300">Thought: {st.thought}</p>
                      <p className="text-emerald-300">Observation: {st.observation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Draft Remedial Quiz Preview + Human-in-the-Loop Approve Button */}
            <div className="p-5 rounded-xl bg-white border border-indigo-200 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider text-indigo-600">
                    Draft & Preview (Not Saved Until Approved)
                  </span>
                  <h3 className="text-base font-bold text-slate-900">{agentDraft.draft_quiz_title}</h3>
                </div>
                <button
                  onClick={approveAndStartQuiz}
                  disabled={agentApproving || !agentDraft.draft_questions?.length}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black uppercase tracking-wider shadow-xs transition-colors flex items-center gap-2 disabled:opacity-60"
                >
                  <Play className="w-4 h-4" />
                  {agentApproving
                    ? (isTeacherView ? 'Assigning Quiz...' : 'Creating Quiz...')
                    : (isTeacherView ? 'Approve & Assign Remedial Quiz' : 'Approve & Start Remedial Quiz')}
                </button>
              </div>

              <div className="space-y-3">
                {agentDraft.draft_questions?.map((dq, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        Q{idx + 1}. {dq.text}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase ${
                          dq.source === 'bank'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}>
                          {dq.source === 'bank' ? 'Question Bank' : 'AI Synthesized'}
                        </span>
                        {dq.skill_names?.map((sk, sIdx) => (
                          <span key={sIdx} className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                            {sk}
                          </span>
                        ))}
                      </div>
                    </div>
                    {dq.misconception_note && (
                      <p className="text-[11px] text-slate-500 italic">
                        Diagnostic Focus: {dq.misconception_note}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center border-b border-slate-200 space-x-2">
        <button
          onClick={() => setActiveTab('roadmap')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'roadmap'
              ? 'border-indigo-600 text-indigo-600 bg-indigo-50/50 rounded-t-xl'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Compass className="w-4 h-4" />
          Topological Learning Roadmap
          {roadmapData?.remediation_roadmap?.length > 0 && (
            <span className="bg-rose-100 text-rose-700 text-xs px-2 py-0.5 rounded-full font-black">
              {roadmapData.remediation_roadmap.length} steps
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('quadrants')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'quadrants'
              ? 'border-indigo-600 text-indigo-600 bg-indigo-50/50 rounded-t-xl'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Clock className="w-4 h-4" />
          Response-Time Effort & Slip Matrix
        </button>

        <button
          onClick={() => setActiveTab('dina')}
          className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'dina'
              ? 'border-indigo-600 text-indigo-600 bg-indigo-50/50 rounded-t-xl'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Layers className="w-4 h-4" />
          Question Breakdown & Skills Inventory
        </button>
      </div>

      {/* TAB 1: TOPOLOGICAL LEARNING ROADMAP */}
      {activeTab === 'roadmap' && (
        <div className="space-y-6">
          <div className="glass-panel p-6 bg-gradient-to-r from-indigo-900 to-slate-900 text-white rounded-2xl shadow-md">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-white/10 rounded-xl">
                <Milestone className="w-8 h-8 text-indigo-300" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold tracking-tight">Your Prescriptive Remediation Sequence</h3>
                <p className="text-slate-300 text-sm mt-1 leading-relaxed">
                  {roadmapData?.debt_advice || "Concepts are topologically sorted using our Prerequisite DAG engine. Solve upstream blockers first to unlock downstream success."}
                </p>
              </div>
            </div>
          </div>

          {studentGraphData.nodes.length > 0 && (
            <PrerequisiteGraph
              nodes={studentGraphData.nodes}
              edges={studentGraphData.edges}
              mode="mastery"
              title="Interactive Concept Mastery & Prerequisite Network Graph"
              subtitle="Nodes are sized by dependency hub impact and colored by live DINA mastery state. Click any concept to inspect blockers or target it with the AI Tutor."
              height={440}
              onNodeAction={(conceptId) => runTutorAgent(conceptId)}
              actionLabel="Target This Topic"
              actionDisabled={agentLoading}
            />
          )}

          {!roadmapData || roadmapData.remediation_roadmap.length === 0 ? (
            <div className="glass-panel p-12 text-center bg-white/80">
              <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-slate-900">Zero Prerequisite Debt Detected!</h3>
              <p className="text-slate-500 max-w-md mx-auto mt-2">
                All foundational topics currently meet or exceed mastery criteria. You are clear to attempt advanced multi-skill examinations.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {roadmapData.remediation_roadmap.map((item) => (
                <div 
                  key={item.concept_id}
                  className={`glass-panel p-6 border transition-all ${
                    item.is_root_blocker 
                      ? 'border-rose-300 bg-rose-50/30 ring-1 ring-rose-200' 
                      : 'border-slate-200 bg-white hover:border-indigo-300'
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-start gap-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black text-base ${
                        item.is_root_blocker ? 'bg-rose-600 text-white shadow-xs' : 'bg-indigo-600 text-white'
                      }`}>
                        #{item.step}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-lg font-bold text-slate-900">{item.concept_name}</h4>
                          {item.is_root_blocker && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider bg-rose-100 text-rose-700 border border-rose-200">
                              Root Blocker
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Current Mastery: <strong className="text-slate-800">{Math.round(item.current_mastery * 100)}%</strong> &bull; Confidence: {Math.round(item.confidence_score * 100)}%
                        </p>
                        {item.unlocks_topics.length > 0 && (
                          <div className="flex items-center gap-1.5 mt-2 text-xs font-semibold text-indigo-600">
                            <Sparkles className="w-3.5 h-3.5" />
                            Fixing this unlocks: {item.unlocks_topics.join(', ')}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => runTutorAgent(item.concept_id)}
                        disabled={agentLoading}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1 disabled:opacity-60"
                      >
                        Target This Topic
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EFFORT & LATENCY QUADRANTS */}
      {activeTab === 'quadrants' && (
        <div className="space-y-6">
          <div className="glass-panel p-6 bg-white shadow-sm border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-600" />
              Cognitive Behavior Distribution (Response-Time Effort)
            </h3>
            <p className="text-sm text-slate-500 mb-6">
              Categorizes response times and accuracy into 4 cognitive behavioral profiles according to psychometric effort theory.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200">
                <span className="text-xs font-black uppercase tracking-wider text-emerald-700">Cognitive Fluency</span>
                <p className="text-3xl font-black text-emerald-900 mt-2">
                  {quadrantData?.cognitive_fluency_pct || 0}%
                </p>
                <p className="text-xs text-emerald-700 mt-1">Optimal Solving Speed & Correct</p>
              </div>

              <div className="p-5 rounded-2xl bg-blue-50/70 border border-blue-200">
                <span className="text-xs font-black uppercase tracking-wider text-blue-700">Deliberate Mastery</span>
                <p className="text-3xl font-black text-blue-900 mt-2">
                  {quadrantData?.deliberate_mastery_pct || 0}%
                </p>
                <p className="text-xs text-blue-700 mt-1">High Thinking Time & Correct</p>
              </div>

              <div className="p-5 rounded-2xl bg-rose-50/70 border border-rose-200">
                <span className="text-xs font-black uppercase tracking-wider text-rose-700">Cognitive Struggle</span>
                <p className="text-3xl font-black text-rose-900 mt-2">
                  {quadrantData?.cognitive_struggle_pct || 0}%
                </p>
                <p className="text-xs text-rose-700 mt-1">High Effort but Conceptual Block</p>
              </div>

              <div className="p-5 rounded-2xl bg-slate-100 border border-slate-300">
                <span className="text-xs font-black uppercase tracking-wider text-slate-700">Rapid Guessing</span>
                <p className="text-3xl font-black text-slate-900 mt-2">
                  {quadrantData?.rapid_guessing_pct || 0}%
                </p>
                <p className="text-xs text-slate-600 mt-1">Answered in &lt; 4s (Low Effort)</p>
              </div>
            </div>
          </div>

          {/* Recent Cognitive Attempts Table */}
          <div className="glass-panel p-6 bg-white shadow-sm border border-slate-200">
            <h4 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-indigo-600" />
              Recent Attempts Latency & Anomaly Diagnostics
            </h4>

            {advancedData?.recent_cognitive_attempts?.length === 0 ? (
              <p className="text-sm text-slate-500 py-4 text-center">No recent test attempts found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 font-bold uppercase text-[11px] border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Question</th>
                      <th className="py-3 px-4">Result</th>
                      <th className="py-3 px-4">Latency vs Expected</th>
                      <th className="py-3 px-4">Cognitive Quadrant</th>
                      <th className="py-3 px-4">Psychometric Diagnostic</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {advancedData?.recent_cognitive_attempts?.map((att, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-3 px-4 max-w-xs truncate font-medium text-slate-800">
                          {att.question_text}
                        </td>
                        <td className="py-3 px-4">
                          {att.is_correct ? (
                            <span className="inline-flex items-center gap-1 text-emerald-600 font-bold text-xs">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Correct
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-rose-600 font-bold text-xs">
                              <AlertCircle className="w-3.5 h-3.5" /> Missed
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-xs font-mono text-slate-700">
                          {att.actual_time_seconds}s / {att.expected_time_seconds}s ({att.latency_ratio}x)
                        </td>
                        <td className="py-3 px-4">
                          <span 
                            className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider"
                            style={{ backgroundColor: `${att.quadrant_color}20`, color: att.quadrant_color }}
                          >
                            {att.quadrant.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs">
                          {att.anomaly_type === 'CARELESS_SLIP' ? (
                            <span className="font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">
                              Careless Slip (P={Math.round(att.predicted_probability * 100)}%)
                            </span>
                          ) : att.anomaly_type === 'RAPID_LUCKY_GUESS' ? (
                            <span className="font-bold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-md">
                              Rapid Lucky Guess
                            </span>
                          ) : (
                            <span className="text-slate-500">Standard Behavior</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: DINA & REQUIRED SKILLS INVENTORY */}
      {activeTab === 'dina' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-500" />
              Missed Questions Root-Cause Analysis
            </h2>

            {report.length === 0 ? (
              <div className="glass-panel p-12 text-center text-slate-500 bg-white">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-900">Zero Missed Questions!</p>
                <p>You have successfully answered all attempted questions.</p>
              </div>
            ) : (
              report.map((item, idx) => (
                <div key={item.question_id} className="glass-panel overflow-hidden border border-slate-200 bg-white">
                  <div className="p-5 bg-slate-50 border-b border-slate-200">
                    <div className="flex items-start gap-3">
                      <span className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs">
                        {idx + 1}
                      </span>
                      <div>
                        <h3 className="text-base font-semibold text-slate-800 leading-tight">
                          {item.question_text}
                        </h3>
                        <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-400 font-semibold">
                          <Info className="w-3 h-3" />
                          CONJUNCTIVE Q-MATRIX EVALUATION
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-5 space-y-3">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Required Skills Breakdown</h4>
                    <div className="grid gap-3">
                      {item.required_skills.map(skill => (
                        <div key={skill.concept_id} className={`p-3 rounded-xl border ${
                          skill.likely_missing 
                            ? 'bg-rose-50/40 border-rose-200' 
                            : 'bg-slate-50/50 border-slate-200'
                        }`}>
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-bold text-slate-900 text-sm">{skill.concept_name}</p>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border ${getReliabilityColor(skill.reliability_tier)}`}>
                                {skill.reliability_tier} RELIABILITY
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="text-sm font-black text-slate-800">
                                {Math.round(skill.adjusted_mastery * 100)}%
                              </span>
                              {skill.likely_missing && (
                                <p className="text-[10px] font-black text-rose-600 uppercase">
                                  Likely Missing
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              Syllabus Skill Inventory
            </h2>
            <div className="glass-panel p-6 space-y-5 bg-white border border-slate-200 sticky top-24">
              {masteryData.sort((a, b) => a.adjusted_mastery - b.adjusted_mastery).map(m => (
                <div key={m.concept_id} className="space-y-1.5">
                  <div className="flex justify-between items-end">
                    <span className="text-xs font-bold text-slate-700">{m.concept_name}</span>
                    <span className={`text-xs font-black ${m.adjusted_mastery < 0.5 ? 'text-rose-600' : 'text-emerald-600'}`}>
                      {Math.round(m.adjusted_mastery * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ${getMasteryColor(m.adjusted_mastery)}`}
                      style={{ width: `${m.adjusted_mastery * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
