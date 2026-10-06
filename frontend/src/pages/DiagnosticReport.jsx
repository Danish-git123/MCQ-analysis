import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import { 
  Brain, 
  AlertCircle, 
  CheckCircle2, 
  HelpCircle, 
  BarChart3, 
  ArrowLeft,
  ChevronRight,
  TrendingDown,
  Info
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function DiagnosticReport() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [report, setReport] = useState([]);
  const [masteryData, setMasteryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      if (user.id) {
        fetchData();
      } else {
        setError("Invalid user session. Please log out and log in again.");
        setLoading(false);
      }
    }
  }, [user]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [reportRes, masteryRes] = await Promise.all([
        api.get(`/diagnosis/student/${user.id}/report`),
        api.get(`/diagnosis/student/${user.id}`)
      ]);
      setReport(reportRes.data);
      setMasteryData(masteryRes.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch diagnostic data:", err);
      setError("Failed to load your diagnostic report. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const getReliabilityColor = (tier) => {
    switch (tier) {
      case 'HIGH': return 'text-emerald-600 bg-emerald-50 border-emerald-100';
      case 'MEDIUM': return 'text-amber-600 bg-amber-50 border-amber-100';
      case 'LOW': return 'text-slate-500 bg-slate-50 border-slate-100';
      default: return 'text-slate-500 bg-slate-50 border-slate-100';
    }
  };

  const getMasteryColor = (mastery) => {
    if (mastery >= 0.75) return 'bg-emerald-500';
    if (mastery >= 0.5) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p className="text-slate-500 animate-pulse">Generating your personalized skill diagnosis...</p>
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

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <button 
            onClick={() => navigate('/student')}
            className="flex items-center text-slate-500 hover:text-indigo-600 mb-2 transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
            Back to Dashboard
          </button>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
            <Brain className="w-10 h-10 text-indigo-600" />
            Skill Mastery Diagnosis
          </h1>
          <p className="text-slate-500 mt-2 text-lg">
            Deep analysis of your learning gaps and required skills.
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 border-l-4 border-indigo-500">
          <div className="flex items-center gap-3 text-indigo-600 mb-2">
            <BarChart3 className="w-5 h-5" />
            <h3 className="font-bold uppercase tracking-wider text-xs">Overall Mastery</h3>
          </div>
          <p className="text-3xl font-black text-slate-900">
            {Math.round(masteryData.reduce((acc, curr) => acc + curr.adjusted_mastery, 0) / (masteryData.length || 1) * 100)}%
          </p>
          <p className="text-sm text-slate-500 mt-1">Average across {masteryData.length} concepts</p>
        </div>
        
        <div className="glass-panel p-6 border-l-4 border-rose-500">
          <div className="flex items-center gap-3 text-rose-600 mb-2">
            <TrendingDown className="w-5 h-5" />
            <h3 className="font-bold uppercase tracking-wider text-xs">Identified Gaps</h3>
          </div>
          <p className="text-3xl font-black text-slate-900">
            {masteryData.filter(m => m.adjusted_mastery < 0.5).length}
          </p>
          <p className="text-sm text-slate-500 mt-1">Skills below 50% mastery</p>
        </div>

        <div className="glass-panel p-6 border-l-4 border-emerald-500">
          <div className="flex items-center gap-3 text-emerald-600 mb-2">
            <CheckCircle2 className="w-5 h-5" />
            <h3 className="font-bold uppercase tracking-wider text-xs">Total Insights</h3>
          </div>
          <p className="text-3xl font-black text-slate-900">{report.length}</p>
          <p className="text-sm text-slate-500 mt-1">Incorrect questions analyzed</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Missing Skills by Question */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <AlertCircle className="w-6 h-6 text-rose-500" />
              Question-Level Analysis
            </h2>
          </div>

          {report.length === 0 ? (
            <div className="glass-panel p-12 text-center text-slate-500">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
              <p className="text-lg font-medium text-slate-900">Great job!</p>
              <p>You haven't missed any questions yet. Keep up the good work!</p>
            </div>
          ) : (
            report.map((item, idx) => (
              <div key={item.question_id} className="glass-panel overflow-hidden border border-slate-200 hover:border-indigo-200 transition-colors group">
                <div className="p-6 bg-slate-50/50 border-b border-slate-200">
                  <div className="flex items-start gap-4">
                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-sm">
                      {idx + 1}
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800 leading-tight">
                        {item.question_text}
                      </h3>
                      <div className="mt-2 flex items-center gap-2 text-xs text-slate-400 font-medium">
                        <Info className="w-3.5 h-3.5" />
                        ANALYSED VIA DINA (Q-MATRIX)
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="p-6 space-y-4">
                  <h4 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Required Skills Analysis</h4>
                  <div className="grid gap-4">
                    {item.required_skills.map(skill => (
                      <div key={skill.concept_id} className={`p-4 rounded-2xl border transition-all ${
                        skill.likely_missing 
                          ? 'bg-rose-50/30 border-rose-100 ring-1 ring-rose-200' 
                          : 'bg-white border-slate-100'
                      }`}>
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          <div className="flex items-start gap-3">
                            {skill.likely_missing ? (
                              <TrendingDown className="w-5 h-5 text-rose-500 mt-0.5" />
                            ) : (
                              <CheckCircle2 className="w-5 h-5 text-emerald-500 mt-0.5" />
                            )}
                            <div>
                              <p className="font-bold text-slate-900">{skill.concept_name}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border ${getReliabilityColor(skill.reliability_tier)}`}>
                                  {skill.reliability_tier} DATA
                                </span>
                                <span className="text-xs text-slate-400">
                                  {skill.opportunity_count} opportunities
                                </span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex flex-col items-end gap-2">
                            <div className="flex items-center gap-3 w-full md:w-48">
                              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full transition-all duration-1000 ${getMasteryColor(skill.adjusted_mastery)}`}
                                  style={{ width: `${skill.adjusted_mastery * 100}%` }}
                                />
                              </div>
                              <span className="text-sm font-black text-slate-700 min-w-[3rem] text-right">
                                {Math.round(skill.adjusted_mastery * 100)}%
                              </span>
                            </div>
                            {skill.likely_missing && (
                              <span className="text-[10px] font-black text-rose-600 bg-rose-100 px-2 py-0.5 rounded-md uppercase tracking-tighter">
                                Likely Missing Prerequisite
                              </span>
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

        {/* Overall Mastery Sidebar */}
        <div className="space-y-6">
          <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-indigo-600" />
            Skill Inventory
          </h2>
          
          <div className="glass-panel p-6 space-y-6 sticky top-24">
            {masteryData.sort((a, b) => a.adjusted_mastery - b.adjusted_mastery).map(m => (
              <div key={m.concept_id} className="space-y-2">
                <div className="flex justify-between items-end">
                  <span className="text-sm font-bold text-slate-700">{m.concept_name}</span>
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
            
            <div className="pt-4 border-t border-slate-100">
              <div className="flex items-start gap-3 p-4 bg-indigo-50 rounded-2xl text-indigo-700 text-xs leading-relaxed">
                <HelpCircle className="w-5 h-5 flex-shrink-0" />
                <p>
                  <strong>How it works:</strong> Our AI uses the DINA model to analyze multiple questions simultaneously. Even if you miss one question, it might be due to a specific missing prerequisite skill shared across other items.
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
