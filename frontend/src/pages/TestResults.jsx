import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Users } from 'lucide-react';
import api from '../api/axios';

export default function TestResults() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [results, setResults] = useState(null);

  useEffect(() => {
    fetchResults();
  }, [id]);

  const fetchResults = async () => {
    try {
      const { data } = await api.get(`/teacher/tests/${id}/results`);
      setResults(data);
    } catch (e) {
      console.error(e);
    }
  };

  if (!results) return <div className="text-center mt-20">Loading...</div>;

  const overallAccuracy = results.total_responses > 0 
    ? Math.round((results.total_correct / results.total_responses) * 100) 
    : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <button onClick={() => navigate('/teacher')} className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Dashboard
      </button>

      <div>
        <h1 className="text-3xl font-bold text-slate-900">Test Results</h1>
        <p className="text-slate-500 mt-1">Overview of student performance</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 flex items-center gap-4">
          <div className="p-4 bg-indigo-50 text-indigo-600 rounded-2xl">
            <Users className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">Total Responses</p>
            <p className="text-3xl font-bold text-slate-900">{results.total_responses}</p>
          </div>
        </div>
        <div className="glass-panel p-6 flex items-center gap-4">
          <div className="p-4 bg-emerald-50 text-emerald-600 rounded-2xl">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 uppercase tracking-wider">Overall Accuracy</p>
            <p className="text-3xl font-bold text-slate-900">{overallAccuracy}%</p>
          </div>
        </div>
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-6">Question Breakdown</h3>
        <div className="space-y-4">
          {Object.entries(results.question_stats).map(([qId, stats], idx) => (
            <div key={qId} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl">
              <span className="font-medium text-slate-700">Question {idx + 1}</span>
              <div className="flex items-center gap-4">
                <span className="text-sm text-slate-500">{stats.correct} / {stats.total} correct</span>
                <div className="w-32 h-2.5 bg-slate-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-indigo-500" 
                    style={{ width: `${(stats.correct / stats.total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
          {Object.keys(results.question_stats).length === 0 && (
            <div className="text-center text-slate-500 py-4">No responses yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
