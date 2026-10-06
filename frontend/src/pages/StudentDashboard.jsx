import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, CheckCircle2, Clock } from 'lucide-react';
import api from '../api/axios';
import { Brain, Sparkles, LayoutDashboard } from 'lucide-react';

export default function StudentDashboard() {
  const [assignments, setAssignments] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    try {
      const { data } = await api.get('/student/assignments');
      setAssignments(data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">My Learning Journey</h1>
          <p className="text-slate-500 mt-1">Track your tests and discover your skill gaps</p>
        </div>
        
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {assignments.map(a => (
          <div key={a.id} className="glass-panel p-6 flex flex-col">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-semibold text-slate-800">{a.test.title}</h3>
              {a.status === 'completed' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Completed
                </span>
              ) : a.status === 'in_progress' ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                  <Clock className="w-3.5 h-3.5" /> In Progress
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-800">
                  Not Started
                </span>
              )}
            </div>
            
            <div className="mt-auto pt-4 border-t border-slate-100">
              {a.status !== 'completed' ? (
                <button 
                  onClick={() => navigate(`/student/take-test/${a.test.id}`)}
                  className="w-full bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 font-medium inline-flex items-center justify-center gap-2 transition-colors"
                >
                  <Play className="w-4 h-4"/> {a.status === 'in_progress' ? 'Resume Test' : 'Start Test'}
                </button>
              ) : (
                <button disabled className="w-full bg-slate-100 text-slate-400 px-4 py-2.5 rounded-xl font-medium cursor-not-allowed">
                  Finished
                </button>
              )}
            </div>
          </div>
        ))}
        {assignments.length === 0 && (
          <div className="col-span-full py-12 text-center text-slate-500 bg-white/50 rounded-2xl border border-dashed border-slate-300">
            You don't have any pending tests right now.
          </div>
        )}
      </div>
    </div>
  );
}
