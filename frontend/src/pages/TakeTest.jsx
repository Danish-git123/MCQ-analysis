import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { CheckCircle2, ArrowRight, Brain } from 'lucide-react';

export default function TakeTest() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [isFinished, setIsFinished] = useState(false);
  
  // Timer ref to calculate response time
  const questionStartTime = useRef(null);

  useEffect(() => {
    fetchQuestions();
  }, [id]);

  const fetchQuestions = async () => {
    try {
      const { data } = await api.get(`/student/tests/${id}/questions`);
      setQuestions(data);
      setLoading(false);
      questionStartTime.current = Date.now();
    } catch (e) {
      alert("Error loading test");
      navigate('/student');
    }
  };

  const handleOptionSelect = async (optionId) => {
    const timeTaken = Date.now() - questionStartTime.current;
    const currentQ = questions[currentIndex];
    
    try {
      await api.post('/student/responses', {
        question_id: currentQ.id,
        selected_option_id: optionId,
        response_time_ms: timeTaken
      });
      
      if (currentIndex < questions.length - 1) {
        setCurrentIndex(currentIndex + 1);
        questionStartTime.current = Date.now();
      } else {
        await api.post(`/student/tests/${id}/complete`);
        setIsFinished(true);
      }
    } catch (e) {
      alert("Error submitting answer");
    }
  };

  if (loading) return <div className="text-center mt-20">Loading...</div>;
  if (!questions.length) return <div className="text-center mt-20">No questions found.</div>;

  if (isFinished) {
    return (
      <div className="max-w-xl mx-auto mt-20 text-center space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="glass-panel p-12">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Test Completed!</h2>
          <p className="text-slate-500 mb-8 text-lg">Your responses have been recorded and our AI is analyzing your performance.</p>
          
          <div className="grid gap-4">
            <button 
              onClick={() => navigate('/student/diagnosis')}
              className="flex items-center justify-between p-6 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700 transition-all group"
            >
              <div className="flex items-center gap-4">
                <div className="bg-white/20 p-2 rounded-xl">
                  <Brain className="w-6 h-6" />
                </div>
                <div className="text-left">
                  <p className="font-bold text-lg">View Diagnostic Report</p>
                  <p className="text-xs opacity-80">Identify your skill gaps immediately</p>
                </div>
              </div>
              <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
            </button>

            <button 
              onClick={() => navigate('/student')}
              className="flex items-center justify-center gap-2 p-4 text-slate-500 font-medium hover:text-slate-800 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const q = questions[currentIndex];

  return (
    <div className="max-w-3xl mx-auto mt-10">
      <div className="mb-6 flex justify-between items-center">
        <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">
          Question {currentIndex + 1} of {questions.length}
        </span>
        <div className="h-2 w-48 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-indigo-600 transition-all duration-300" 
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          />
        </div>
      </div>

      <div className="glass-panel p-8 md:p-12">
        <h2 className="text-2xl font-semibold text-slate-900 mb-8">{q.text}</h2>
        <div className="space-y-4">
          {q.options.map(o => (
            <button
              key={o.id}
              onClick={() => handleOptionSelect(o.id)}
              className="w-full text-left p-5 rounded-xl border-2 border-slate-100 bg-white hover:border-indigo-500 hover:bg-indigo-50 transition-all font-medium text-slate-700 shadow-sm"
            >
              {o.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
