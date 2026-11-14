import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Users,
  Bot,
  Sparkles,
  Brain,
  Send,
  AlertTriangle,
  Zap,
  Clock,
  Layers,
  ExternalLink,
  RefreshCw,
  Award,
  BarChart3,
  CheckSquare,
  Square,
  Circle,
} from 'lucide-react';
import api from '../api/axios';
import PrerequisiteGraph from '../components/PrerequisiteGraph';

export default function TestResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [interventionDraft, setInterventionDraft] = useState(null);
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [agentLoading, setAgentLoading] = useState(false);
  const [agentApproving, setAgentApproving] = useState(false);
  const [agentMessage, setAgentMessage] = useState('');
  const [agentError, setAgentError] = useState('');

  useEffect(() => {
    const loadResults = async () => {
      try {
        setLoading(true);
        const { data } = await api.get(`/teacher/tests/${id}/results`);
        setResults(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    loadResults();
  }, [id]);

  const refreshResults = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/teacher/tests/${id}/results`);
      setResults(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const cohortGraphData = useMemo(() => {
    const cg = results?.cohort_graph;
    if (!cg) return { nodes: [], edges: [] };
    const nodes = (cg.nodes || []).map((n) => ({
      id: String(n.concept_id),
      conceptId: n.concept_id,
      label: n.name,
      mastery: n.avg_mastery,
      isRootBlocker: Boolean(n.is_root_blocker),
      description:
        n.class_accuracy_pct != null
          ? `Class Question Accuracy: ${n.class_accuracy_pct}% (${n.attempts} attempts)`
          : 'Connected prerequisite syllabus concept',
    }));
    const edges = (cg.edges || []).map((e) => ({
      id: `cohort-e-${e.id}`,
      from: String(e.from_concept_id),
      to: String(e.to_concept_id),
      confidence: e.confidence ?? 0.85,
      reasoning: e.source ? `Source: ${e.source}` : '',
    }));
    return { nodes, edges };
  }, [results]);

  const runClassInterventionAgent = async () => {
    setAgentLoading(true);
    setAgentMessage('');
    setAgentError('');
    try {
      const { data } = await api.post(`/agent/teacher/tests/${id}/intervention-draft`, {
        max_questions: 4,
      });
      setInterventionDraft(data);
      setSelectedStudentIds((data.struggling_students || []).map((s) => s.student_id));
    } catch (e) {
      setAgentError(e.response?.data?.detail || 'Failed to run Class Intervention Agent.');
    } finally {
      setAgentLoading(false);
    }
  };

  const toggleTargetStudent = (sid) => {
    setSelectedStudentIds((prev) =>
      prev.includes(sid) ? prev.filter((x) => x !== sid) : [...prev, sid]
    );
  };

  const toggleAllTargetStudents = () => {
    const allIds = (interventionDraft?.struggling_students || []).map((s) => s.student_id);
    if (selectedStudentIds.length === allIds.length) {
      setSelectedStudentIds([]);
    } else {
      setSelectedStudentIds(allIds);
    }
  };

  const updateDraftQuestionText = (qIdx, val) => {
    setInterventionDraft((prev) => {
      if (!prev) return prev;
      const nextQs = prev.draft_questions.map((q, i) => (i === qIdx ? { ...q, text: val } : q));
      return { ...prev, draft_questions: nextQs };
    });
  };

  const updateDraftOptionText = (qIdx, oIdx, val) => {
    setInterventionDraft((prev) => {
      if (!prev) return prev;
      const nextQs = prev.draft_questions.map((q, i) => {
        if (i !== qIdx) return q;
        const nextOpts = q.options.map((o, oi) => (oi === oIdx ? { ...o, text: val } : o));
        return { ...q, options: nextOpts };
      });
      return { ...prev, draft_questions: nextQs };
    });
  };

  const setDraftCorrectOption = (qIdx, oIdx) => {
    setInterventionDraft((prev) => {
      if (!prev) return prev;
      const nextQs = prev.draft_questions.map((q, i) => {
        if (i !== qIdx) return q;
        const nextOpts = q.options.map((o, oi) => ({ ...o, is_correct: oi === oIdx }));
        return { ...q, options: nextOpts };
      });
      return { ...prev, draft_questions: nextQs };
    });
  };

  const approveClassIntervention = async () => {
    if (!interventionDraft) return;
    if (selectedStudentIds.length === 0) {
      setAgentError('Please select at least one student to assign this revision quiz.');
      return;
    }
    setAgentApproving(true);
    setAgentMessage('');
    setAgentError('');
    try {
      const { data } = await api.post(`/agent/teacher/tests/${id}/intervention-approve`, {
        title: interventionDraft.draft_quiz_title,
        student_ids: selectedStudentIds,
        questions: interventionDraft.draft_questions,
      });
      setAgentMessage(
        `Approved & assigned "${data.title}" (${data.question_count} questions) to ${data.assigned_student_ids.length} student(s).`
      );
    } catch (e) {
      setAgentError(e.response?.data?.detail || 'Failed to assign revision quiz.');
    } finally {
      setAgentApproving(false);
    }
  };

  if (loading && !results) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[55vh] space-y-3">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
        <p className="text-sm text-slate-500 font-medium">Loading cohort analytics & psychometrics...</p>
      </div>
    );
  }

  if (!results) {
    return <div className="text-center mt-20 text-slate-500">Could not load test results.</div>;
  }

  const summary = results.summary || {};
  const overallAccuracy =
    summary.overall_accuracy_pct ??
    (results.total_responses > 0
      ? Math.round((results.total_correct / results.total_responses) * 100)
      : 0);

  const heatmapConcepts = results.concept_heatmap?.concepts || [];
  const heatmapStudents = results.concept_heatmap?.students || [];
  const heatmapCells = results.concept_heatmap?.cells || {};
  const questionAnalytics = results.question_analytics || [];

  const getCellStyle = (mastery) => {
    if (mastery == null) return 'bg-slate-100 text-slate-400 border-slate-200';
    if (mastery >= 0.7) return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    if (mastery >= 0.5) return 'bg-amber-50 text-amber-800 border-amber-200';
    return 'bg-rose-50 text-rose-800 border-rose-200';
  };

  const getEffortBadge = (status) => {
    switch (status) {
      case 'RAPID_GUESSING_RISK':
        return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'NEEDS_SUPPORT':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'DEVELOPING':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'ON_TRACK':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      default:
        return 'bg-slate-100 text-slate-500 border-slate-200';
    }
  };

  const getQualityBadge = (quality) => {
    switch (quality) {
      case 'STRONG':
        return { cls: 'bg-emerald-100 text-emerald-800 border-emerald-200', label: 'Strong Discrimination' };
      case 'FAIR':
        return { cls: 'bg-blue-100 text-blue-800 border-blue-200', label: 'Fair Discrimination' };
      case 'REVIEW_NEEDED':
        return { cls: 'bg-rose-100 text-rose-800 border-rose-200', label: 'Review Item Quality' };
      default:
        return { cls: 'bg-slate-100 text-slate-500 border-slate-200', label: 'Needs More Samples' };
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/teacher')}
            className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors text-sm font-semibold mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </button>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">
            {results.test_title || 'Test Results'}
          </h1>
          <p className="text-slate-500 mt-1 text-sm">
            Cohort psychometric diagnostics, Student &times; Concept mastery heatmap, distractor traps, and prerequisite bottlenecks.
          </p>
        </div>
        <button
          onClick={refreshResults}
          disabled={loading}
          className="px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 flex items-center gap-1.5 self-start shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Analytics
        </button>
      </div>

      {/* Top 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 flex items-center gap-4 border-l-4 border-indigo-500 bg-white/85">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl">
            <Users className="w-7 h-7" />
          </div>
          <div>
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Cohort Responses</p>
            <p className="text-2xl font-black text-slate-900">{results.total_responses}</p>
            <p className="text-[11px] text-slate-500">
              {summary.students_evaluated ?? 0} / {summary.assigned_count ?? 0} students active
            </p>
          </div>
        </div>

        <div className="glass-panel p-5 flex items-center gap-4 border-l-4 border-emerald-500 bg-white/85">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-2xl">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <div>
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Overall Accuracy</p>
            <p className="text-2xl font-black text-slate-900">{overallAccuracy}%</p>
            <p className="text-[11px] text-slate-500">
              Avg solving time: {summary.avg_response_time_sec ?? 0}s
            </p>
          </div>
        </div>

        <div className="glass-panel p-5 flex items-center gap-4 border-l-4 border-rose-500 bg-white/85">
          <div className="p-3 bg-rose-50 text-rose-600 rounded-2xl">
            <Zap className="w-7 h-7" />
          </div>
          <div>
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Rapid Guessing (&lt;4s)</p>
            <p className="text-2xl font-black text-slate-900">{summary.rapid_guessing_pct ?? 0}%</p>
            <p className="text-[11px] text-rose-600 font-semibold">Low-effort rush signal</p>
          </div>
        </div>

        <div className="glass-panel p-5 flex items-center gap-4 border-l-4 border-amber-500 bg-white/85">
          <div className="p-3 bg-amber-50 text-amber-600 rounded-2xl">
            <Layers className="w-7 h-7" />
          </div>
          <div>
            <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Concepts Assessed</p>
            <p className="text-2xl font-black text-slate-900">{summary.concepts_covered ?? heatmapConcepts.length}</p>
            <p className="text-[11px] text-slate-500">{questionAnalytics.length} Q-Matrix items</p>
          </div>
        </div>
      </div>

      {/* Cohort Prerequisite Bottleneck Network Graph */}
      {cohortGraphData.nodes.length > 0 && (
        <PrerequisiteGraph
          nodes={cohortGraphData.nodes}
          edges={cohortGraphData.edges}
          mode="mastery"
          title="Cohort Prerequisite Bottleneck Network Graph"
          subtitle="Visualizes class average DINA mastery per syllabus concept and highlights upstream Root Blockers dragging down downstream skills."
          height={400}
        />
      )}

      {/* Student x Concept Mastery Heatmap & Effort Risk Table */}
      <div className="glass-panel p-6 bg-white border border-slate-200 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-600" />
              Student &times; Concept DINA Mastery Heatmap
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any student row&rsquo;s <strong>Inspect Dossier</strong> button to view their personal DAG roadmap, BKT forgetting curve, and AI Tutor analysis.
            </p>
          </div>
        </div>

        {heatmapStudents.length === 0 ? (
          <div className="text-center text-slate-500 py-6 text-sm">
            No students assigned or evaluated on this test yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase text-[10px] font-black tracking-wider">
                  <th className="py-3 px-3">Student</th>
                  <th className="py-3 px-3">Accuracy</th>
                  <th className="py-3 px-3">Effort / Anomalies</th>
                  {heatmapConcepts.map((c) => (
                    <th key={c.concept_id} className="py-3 px-2.5 text-center max-w-[130px] truncate" title={c.concept_name}>
                      {c.concept_name}
                    </th>
                  ))}
                  <th className="py-3 px-3 text-right">Dossier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {heatmapStudents.map((st) => (
                  <tr key={st.student_id} className="hover:bg-slate-50/70">
                    <td className="py-3 px-3">
                      <p className="font-bold text-slate-900">{st.name}</p>
                      <p className="text-[11px] text-slate-400">{st.email}</p>
                    </td>
                    <td className="py-3 px-3">
                      {st.accuracy_pct != null ? (
                        <div>
                          <span className="font-black text-slate-900">{st.accuracy_pct}%</span>
                          <p className="text-[10px] text-slate-400">
                            {st.answered_count} ans &bull; {st.avg_time_sec}s avg
                          </p>
                        </div>
                      ) : (
                        <span className="text-slate-400 font-medium">Not started</span>
                      )}
                    </td>
                    <td className="py-3 px-3 space-y-1">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-black border ${getEffortBadge(st.effort_status)}`}>
                        {st.effort_status.replace(/_/g, ' ')}
                      </span>
                      {(st.rapid_guess_count > 0 || st.careless_slip_count > 0) && (
                        <div className="flex flex-wrap gap-1 text-[10px]">
                          {st.rapid_guess_count > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                              {st.rapid_guess_count} rapid (&lt;4s)
                            </span>
                          )}
                          {st.careless_slip_count > 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold">
                              {st.careless_slip_count} slip(s)
                            </span>
                          )}
                        </div>
                      )}
                    </td>

                    {heatmapConcepts.map((c) => {
                      const cell = heatmapCells[String(st.student_id)]?.[String(c.concept_id)] || {};
                      const m = cell.mastery;
                      return (
                        <td key={c.concept_id} className="py-2.5 px-2 text-center">
                          <div className={`px-2 py-1.5 rounded-lg border font-bold ${getCellStyle(m)}`}>
                            <div>{m != null ? `${Math.round(m * 100)}%` : '—'}</div>
                            {cell.tier && cell.tier !== 'UNTESTED' && (
                              <div className="text-[9px] font-semibold opacity-75">{cell.tier}</div>
                            )}
                          </div>
                        </td>
                      );
                    })}

                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => navigate(`/teacher/student/${st.student_id}/diagnosis`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-bold text-[11px] border border-indigo-200 transition-colors"
                      >
                        Inspect <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Item Psychometrics & Distractor Trap Analysis */}
      <div className="glass-panel p-6 bg-white border border-slate-200 space-y-5">
        <div>
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-5 h-5 text-indigo-600" />
            Item Psychometrics &amp; Distractor Magnet Analysis
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Shows Point-Biserial Discrimination Index (item quality), response speed, Q-matrix tags, and exact wrong options pulling students off track.
          </p>
        </div>

        <div className="space-y-4">
          {questionAnalytics.map((qa) => {
            const qBadge = getQualityBadge(qa.item_quality);
            return (
              <div key={qa.question_id} className="p-4 rounded-2xl bg-slate-50/70 border border-slate-200 space-y-3">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-2">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-slate-800 text-white text-[10px] font-black">
                        Q{qa.question_number}
                      </span>
                      <span className="font-bold text-slate-900 text-sm">{qa.text}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {(qa.required_skills || []).map((sk, si) => (
                        <span
                          key={si}
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${
                            sk.is_primary
                              ? 'bg-indigo-100 text-indigo-800 border-indigo-200'
                              : 'bg-purple-50 text-purple-700 border-purple-200'
                          }`}
                        >
                          {sk.concept_name} {sk.is_primary ? '(Primary)' : `(${sk.source})`}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
                    <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black border ${qBadge.cls}`}>
                      {qBadge.label}
                      {qa.discrimination_index != null ? ` (r=${qa.discrimination_index})` : ''}
                    </span>
                    <span className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white border border-slate-200 text-slate-700">
                      {qa.correct}/{qa.attempts} ({qa.accuracy_pct}%)
                    </span>
                    <span className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-white border border-slate-200 text-slate-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {qa.avg_time_sec}s
                    </span>
                  </div>
                </div>

                {/* Option Distribution Bars */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  {(qa.option_distribution || []).map((opt) => (
                    <div
                      key={opt.option_id}
                      className={`p-2.5 rounded-xl border text-xs space-y-1 ${
                        opt.is_correct
                          ? 'bg-emerald-50/70 border-emerald-300'
                          : opt.is_top_distractor
                          ? 'bg-rose-50/70 border-rose-300'
                          : 'bg-white border-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-800 truncate" title={opt.text}>
                          <strong>{opt.letter})</strong> {opt.text}
                        </span>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {opt.is_correct && (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-600 text-white text-[9px] font-black uppercase">
                              Correct
                            </span>
                          )}
                          {opt.is_top_distractor && (
                            <span className="px-1.5 py-0.5 rounded bg-rose-600 text-white text-[9px] font-black uppercase">
                              Top Trap
                            </span>
                          )}
                          <span className="font-mono font-bold text-slate-700">
                            {opt.count} ({opt.pct}%)
                          </span>
                        </div>
                      </div>
                      <div className="h-1.5 w-full bg-slate-200/70 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            opt.is_correct
                              ? 'bg-emerald-500'
                              : opt.is_top_distractor
                              ? 'bg-rose-500'
                              : 'bg-slate-400'
                          }`}
                          style={{ width: `${opt.pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {questionAnalytics.length === 0 && (
            <div className="text-center text-slate-500 py-4 text-sm">No questions found in this test.</div>
          )}
        </div>
      </div>

      {/* Class Intervention Agent Panel */}
      <div className="glass-panel p-6 border border-indigo-200 bg-gradient-to-br from-indigo-50/70 via-white to-slate-50 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-3 rounded-xl bg-indigo-600 text-white">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">Class Intervention AI Agent</h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Diagnoses class-wide Q-matrix bottlenecks, rapid-guessing fatigue, and high-miss traps to draft a customizable revision quiz.
              </p>
            </div>
          </div>
          <button
            onClick={runClassInterventionAgent}
            disabled={agentLoading}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold flex items-center gap-2 disabled:opacity-60"
          >
            <Sparkles className="w-4 h-4" />
            {agentLoading ? 'Analyzing Cohort...' : 'Analyze Class with AI Agent'}
          </button>
        </div>

        {agentError && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
            {agentError}
          </div>
        )}

        {agentMessage && (
          <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
            {agentMessage}
          </div>
        )}

        {interventionDraft && (
          <div className="space-y-4 pt-4 border-t border-indigo-100">
            <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-black uppercase text-indigo-700">Teaching Briefing</span>
                <span className="font-mono text-slate-500">Engine: {interventionDraft.engine_mode}</span>
              </div>
              <p className="text-sm text-slate-800 font-medium">{interventionDraft.teaching_briefing}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-2">
                <p className="text-xs font-black uppercase text-rose-700 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Concept Bottlenecks
                </p>
                {interventionDraft.bottleneck_concepts?.map((b, i) => (
                  <div key={i} className="flex justify-between text-xs py-1 border-b border-slate-100 last:border-0">
                    <span className="font-semibold text-slate-800">{b.concept_name}</span>
                    <span className="font-black text-rose-600">{b.error_rate_pct}% error</span>
                  </div>
                ))}
                {!interventionDraft.bottleneck_concepts?.length && (
                  <p className="text-xs text-slate-400">None detected yet.</p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-2">
                <p className="text-xs font-black uppercase text-amber-700 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5" /> High-Miss / Slip Alerts
                </p>
                {interventionDraft.high_slip_alerts?.map((h, i) => (
                  <div key={i} className="text-xs py-1 border-b border-slate-100 last:border-0 space-y-0.5">
                    <p className="font-semibold text-slate-800 line-clamp-2">{h.question_text}</p>
                    <p className="text-[11px] text-amber-700 font-bold">
                      {h.miss_rate_pct}% miss rate &bull; {h.skills?.join(', ')}
                    </p>
                  </div>
                ))}
                {!interventionDraft.high_slip_alerts?.length && (
                  <p className="text-xs text-slate-400">No high-miss trap items flagged.</p>
                )}
              </div>

              <div className="p-4 rounded-xl bg-slate-900 text-slate-100 space-y-1.5 font-mono text-[11px]">
                <p className="text-indigo-300 font-bold flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5" /> Reasoning Trace
                </p>
                {interventionDraft.reasoning_trace?.map((st) => (
                  <p key={st.step} className="text-slate-300">
                    [{st.step}] {st.tool_name}: {st.observation}
                  </p>
                ))}
              </div>
            </div>

            {/* Selective Student Targeting + Editable Draft Preview */}
            <div className="p-4 rounded-xl bg-white border border-indigo-200 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[10px] font-black uppercase text-indigo-600">
                    Editable Draft Revision Quiz &amp; Selective Assignment
                  </span>
                  <h4 className="text-base font-bold text-slate-900">{interventionDraft.draft_quiz_title}</h4>
                </div>
                <button
                  onClick={approveClassIntervention}
                  disabled={agentApproving || selectedStudentIds.length === 0}
                  className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 disabled:opacity-60"
                >
                  <Send className="w-3.5 h-3.5" />
                  {agentApproving
                    ? 'Assigning...'
                    : `Approve & Assign to ${selectedStudentIds.length} Student(s)`}
                </button>
              </div>

              {/* Target Student Checkboxes */}
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700">
                    Target Students ({selectedStudentIds.length} / {interventionDraft.struggling_students?.length || 0} selected)
                  </span>
                  {(interventionDraft.struggling_students?.length || 0) > 0 && (
                    <button
                      type="button"
                      onClick={toggleAllTargetStudents}
                      className="text-indigo-600 hover:underline font-semibold"
                    >
                      {selectedStudentIds.length === interventionDraft.struggling_students.length
                        ? 'Deselect All'
                        : 'Select All'}
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {(interventionDraft.struggling_students || []).map((s) => {
                    const checked = selectedStudentIds.includes(s.student_id);
                    return (
                      <button
                        type="button"
                        key={s.student_id}
                        onClick={() => toggleTargetStudent(s.student_id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold border flex items-center gap-1.5 transition-colors ${
                          checked
                            ? 'bg-indigo-50 border-indigo-300 text-indigo-800'
                            : 'bg-white border-slate-200 text-slate-500'
                        }`}
                      >
                        {checked ? (
                          <CheckSquare className="w-3.5 h-3.5 text-indigo-600" />
                        ) : (
                          <Square className="w-3.5 h-3.5 text-slate-400" />
                        )}
                        {s.name} ({s.accuracy_pct}%)
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Editable Questions */}
              <div className="space-y-3">
                {interventionDraft.draft_questions?.map((dq, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-black text-indigo-700">Q{i + 1} (Editable)</span>
                      <span className="text-slate-500 font-semibold">
                        Skills: {dq.skill_names?.join(', ')}
                      </span>
                    </div>
                    <input
                      type="text"
                      value={dq.text}
                      onChange={(e) => updateDraftQuestionText(i, e.target.value)}
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-semibold text-slate-800"
                    />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {(dq.options || []).map((opt, oi) => (
                        <div key={oi} className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => setDraftCorrectOption(i, oi)}
                            className="text-slate-400 hover:text-emerald-600"
                            title="Mark as correct option"
                          >
                            {opt.is_correct ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Circle className="w-4 h-4" />
                            )}
                          </button>
                          <input
                            type="text"
                            value={opt.text}
                            onChange={(e) => updateDraftOptionText(i, oi, e.target.value)}
                            className={`flex-1 rounded-lg border px-2.5 py-1.5 text-xs ${
                              opt.is_correct
                                ? 'bg-emerald-50 border-emerald-300 font-semibold'
                                : 'bg-white border-slate-200'
                            }`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
