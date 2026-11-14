import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, CheckCircle2, Clock, RefreshCw, AlertCircle } from 'lucide-react';
import api from '../api/axios';
import { Brain, Sparkles } from 'lucide-react';

export default function StudentDashboard() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const { data } = await api.get('/student/assignments');
      setAssignments(data);
    } catch (e) {
      console.error('Failed to fetch assignments:', e);
      setErrorMsg(e.response?.data?.detail || 'Unable to connect to the backend server. Please make sure the backend is running and restart Vite.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">My Learning Journey</h1>
          <p className="text-slate-500 mt-1">Track your tests and discover your skill gaps</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={fetchAssignments}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold text-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Tests
          </button>

          <button 
            onClick={() => navigate('/student/diagnosis')}
            className="group relative flex items-center gap-4 p-4 bg-gradient-to-br from-indigo-600 to-purple-700 rounded-2xl text-white shadow-lg shadow-indigo-200 hover:shadow-xl hover:shadow-indigo-300 transition-all hover:-translate-y-1 overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-125 transition-transform">
              <Sparkles className="w-12 h-12" />
            </div>
            <div className="bg-white/20 p-2.5 rounded-xl">
              <Brain className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="text-xs font-bold uppercase tracking-widest opacity-80">Deep Analysis</p>
              <p className="font-bold text-lg leading-tight">Diagnostic Report</p>
            </div>
            <div className="ml-2 bg-white/20 p-1.5 rounded-full group-hover:translate-x-1 transition-transform">
              <Play className="w-4 h-4 fill-current" />
            </div>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-700 text-sm font-semibold">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {assignments.map(a => (
          <div key={a.id} className="glass-panel p-6 flex flex-col bg-white border border-slate-200 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-bold text-slate-800">{a.test?.title || 'Diagnostic Test'}</h3>
              {a.status === 'completed' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                </span>
              ) : a.status === 'in_progress' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                  <Clock className="w-3.5 h-3.5" /> In Progress
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700">
                  Not Started
                </span>
              )}
            </div>
            
            <p className="text-xs text-slate-400 mb-6">
              Assigned: {a.test?.questions?.length || 6} Questions &bull; Multi-Attribute Psychometric Diagnostic
            </p>

            <div className="mt-auto pt-4 border-t border-slate-100">
              {a.status !== 'completed' ? (
                <button 
                  onClick={() => navigate(`/student/take-test/${a.test.id}`)}
                  className="w-full bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 font-bold inline-flex items-center justify-center gap-2 transition-colors shadow-xs"
                >
                  <Play className="w-4 h-4"/> {a.status === 'in_progress' ? 'Resume Test' : 'Start Test'}
                </button>
              ) : (
                <button disabled className="w-full bg-slate-100 text-slate-400 px-4 py-2.5 rounded-xl font-bold cursor-not-allowed">
                  Finished
                </button>
              )}
            </div>
          </div>
        ))}
        {!loading && assignments.length === 0 && !errorMsg && (
          <div className="col-span-full py-12 text-center text-slate-500 bg-white/50 rounded-2xl border border-dashed border-slate-300">
            You don't have any pending tests right now.
          </div>
        )}
      </div>
    </div>
  );
}
