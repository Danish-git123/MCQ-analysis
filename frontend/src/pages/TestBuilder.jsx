import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle, Upload, Play } from 'lucide-react';
import api from '../api/axios';

export default function TestBuilder() {
  const [title, setTitle] = useState('');
  const [concepts, setConcepts] = useState([]);
  const [newConceptName, setNewConceptName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [questions, setQuestions] = useState([
    { text: '', concept_id: '', options: [{ text: '', is_correct: true }, { text: '', is_correct: false }] }
  ]);
  const [bulkText, setBulkText] = useState('');
  const [bulkErrors, setBulkErrors] = useState([]);
  const [isParsing, setIsParsing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchConcepts();
  }, []);

  const fetchConcepts = async () => {
    try {
      const { data } = await api.get('/teacher/concepts');
      setConcepts(data);
    } catch (err) {
      if (err.response?.status === 403) {
        setErrorMsg('Forbidden (403): You are logged in with a Student account. Please log out and sign in with a Teacher account to create tests.');
      } else {
        console.error('Failed to fetch concepts', err);
      }
    }
  };

  const addConcept = async () => {
    if (!newConceptName.trim()) return;
    setErrorMsg('');
    try {
      const { data } = await api.post('/teacher/concepts', { name: newConceptName.trim() });
      setConcepts(prev => [...prev, data]);
      setNewConceptName('');
    } catch (err) {
      if (err.response?.status === 403) {
        setErrorMsg('Forbidden (403): Teacher role required to create concepts. Please sign in with a Teacher account.');
      } else {
        setErrorMsg(err.response?.data?.detail || 'Failed to create concept');
      }
    }
  };

  const addQuestion = () => {
    setQuestions([...questions, { text: '', concept_id: '', options: [{ text: '', is_correct: true }, { text: '', is_correct: false }] }]);
  };

  const removeQuestion = (qIndex) => {
    if (questions.length === 1) {
      alert('A test must contain at least one question.');
      return;
    }
    setQuestions(questions.filter((_, idx) => idx !== qIndex));
  };

  const addOption = (qIndex) => {
    const newQs = [...questions];
    newQs[qIndex].options.push({ text: '', is_correct: false });
    setQuestions(newQs);
  };

  const removeOption = (qIndex, oIndex) => {
    const newQs = [...questions];
    if (newQs[qIndex].options.length <= 2) {
      alert('Each question must have at least 2 options.');
      return;
    }
    const wasCorrect = newQs[qIndex].options[oIndex].is_correct;
    newQs[qIndex].options = newQs[qIndex].options.filter((_, idx) => idx !== oIndex);
    if (wasCorrect && newQs[qIndex].options.length > 0) {
      newQs[qIndex].options[0].is_correct = true;
    }
    setQuestions(newQs);
  };

  const markCorrect = (qIndex, oIndex) => {
    const newQs = [...questions];
    newQs[qIndex].options = newQs[qIndex].options.map((o, idx) => ({ ...o, is_correct: idx === oIndex }));
    setQuestions(newQs);
  };

  const updateQuestion = (qIndex, field, value) => {
    const newQs = [...questions];
    newQs[qIndex][field] = value;
    setQuestions(newQs);
  };

  const updateOption = (qIndex, oIndex, value) => {
    const newQs = [...questions];
    newQs[qIndex].options[oIndex].text = value;
    setQuestions(newQs);
  };

  const saveTest = async () => {
    setErrorMsg('');
    if (!title.trim()) {
      setErrorMsg('Please enter a Test Title before saving.');
      return;
    }
    for (let i = 0; i < questions.length; i++) {
      if (!questions[i].text.trim()) {
        setErrorMsg(`Question ${i + 1} is empty. Please fill in all question texts.`);
        return;
      }
      for (let j = 0; j < questions[i].options.length; j++) {
        if (!questions[i].options[j].text.trim()) {
          setErrorMsg(`Question ${i + 1}, Option ${j + 1} is empty.`);
          return;
        }
      }
    }

    const payloadQuestions = questions.map(q => {
      const cid = parseInt(q.concept_id);
      return {
        text: q.text.trim(),
        concept_id: isNaN(cid) ? null : cid,
        options: q.options.map(o => ({ text: o.text.trim(), is_correct: o.is_correct }))
      };
    });

    try {
      await api.post('/teacher/tests', { title: title.trim(), questions: payloadQuestions });
      navigate('/teacher');
    } catch (e) {
      if (e.response?.status === 403) {
        setErrorMsg('Forbidden (403): You are logged in with a Student account. Please log out and sign in as Teacher to create tests.');
      } else {
        setErrorMsg(e.response?.data?.detail || 'Error saving test. Please check all fields.');
      }
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setBulkText(event.target.result);
    };
    reader.readAsText(file);
    e.target.value = null; // reset input
  };

  const parseBulkQuestions = async () => {
    if (!bulkText.trim()) return;
    setIsParsing(true);
    setBulkErrors([]);
    try {
      const { data } = await api.post('/teacher/tests/parse-bulk-questions', { raw_text: bulkText });
      
      if (data.errors && data.errors.length > 0) {
        setBulkErrors(data.errors);
      }

      if (data.questions && data.questions.length > 0) {
        const parsedQs = data.questions.map(q => ({
          text: q.text,
          concept_id: q.concept_id ? q.concept_id.toString() : (q.concept_name || ''),
          concept_name: q.concept_name, // keep track for the dropdown
          options: q.options
        }));
        
        // Append to existing questions, but if the default empty question is there, replace it
        if (questions.length === 1 && !questions[0].text && questions[0].options[0].text === '') {
          setQuestions(parsedQs);
        } else {
          setQuestions(prev => [...prev, ...parsedQs]);
        }
        
        // Clear textarea on success
        setBulkText('');
      }
    } catch (err) {
      console.error('Failed to parse questions', err);
      setBulkErrors([{ question_number: "Error", message: err.response?.data?.detail || 'Failed to parse questions from the server.' }]);
    } finally {
      setIsParsing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900">Create Test</h1>
        <button onClick={saveTest} className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-medium shadow-md hover:bg-indigo-700 transition-colors">
          Save Test
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl font-medium flex items-center gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="glass-panel p-6">
        <label className="block text-sm font-semibold text-slate-800">Test Title</label>
        <input 
          type="text" 
          placeholder="e.g. Midterm: Networking Basics"
          className="mt-2 block w-full rounded-xl border-slate-200 bg-white/50 px-4 py-3 text-lg focus:border-indigo-500 focus:ring-indigo-500" 
          value={title} onChange={e => setTitle(e.target.value)}
        />
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Manage Concepts</h3>
        <div className="flex gap-2">
          <input 
            type="text" placeholder="New Concept Name (e.g. TCP Handshake)"
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5"
            value={newConceptName} onChange={e => setNewConceptName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') addConcept(); }}
          />
          <button onClick={addConcept} className="bg-slate-800 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-slate-700 transition-colors">
            Add Concept
          </button>
        </div>
      </div>

      <div className="glass-panel p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Bulk Import Questions</h3>
        <div className="space-y-4">
          <textarea 
            className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 min-h-[200px] focus:border-indigo-500"
            placeholder="Paste your questions here...&#10;&#10;Q1 — Concept: `Networking`&#10;What is a router?&#10;A) A device&#10;B) A cable&#10;Answer: A"
            value={bulkText}
            onChange={e => setBulkText(e.target.value)}
          ></textarea>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={parseBulkQuestions}
              disabled={isParsing || !bulkText.trim()}
              className="bg-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              {isParsing ? 'Parsing...' : 'Parse Questions'}
            </button>
            <div className="relative">
              <input 
                type="file" 
                accept=".txt,.md" 
                onChange={handleFileUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <button className="bg-white border border-slate-200 text-slate-700 px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-slate-50 transition-colors flex items-center gap-2">
                <Upload className="w-4 h-4" />
                Upload File (.txt, .md)
              </button>
            </div>
          </div>
        </div>
      </div>

      {bulkErrors.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl space-y-2">
          <div className="font-semibold flex items-center gap-2">
            <AlertCircle className="w-5 h-5" /> Import Issues
          </div>
          <ul className="list-disc list-inside text-sm pl-2">
            {bulkErrors.map((err, idx) => (
              <li key={idx}><strong>{err.question_number}:</strong> {err.message}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-6">
        {questions.map((q, qIndex) => (
          <div key={qIndex} className="glass-panel p-6 border-l-4 border-indigo-500 relative">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold text-slate-800 text-lg">Question {qIndex + 1}</h3>
              <div className="flex items-center gap-3">
                <select 
                  className="rounded-xl border-slate-200 text-sm bg-white px-3 py-1.5 focus:border-indigo-500 max-w-[200px] truncate"
                  value={q.concept_id} onChange={e => updateQuestion(qIndex, 'concept_id', e.target.value)}
                >
                  <option value="">Select Concept (Optional)...</option>
                  {concepts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  {q.concept_name && q.concept_id === q.concept_name && (
                    <option value={q.concept_name}>{q.concept_name} (Unsaved)</option>
                  )}
                </select>
                {questions.length > 1 && (
                  <button 
                    onClick={() => removeQuestion(qIndex)}
                    title="Delete Question"
                    className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>
            
            <input 
              type="text" placeholder="Question text..."
              className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 mb-6 focus:border-indigo-500"
              value={q.text} onChange={e => updateQuestion(qIndex, 'text', e.target.value)}
            />

            <div className="space-y-3 pl-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
                Options (Click circle to select correct answer)
              </span>
              {q.options.map((o, oIndex) => (
                <div key={oIndex} className="flex items-center gap-3">
                  <button onClick={() => markCorrect(qIndex, oIndex)} className="text-slate-400 hover:text-indigo-600 transition-colors">
                    {o.is_correct ? <CheckCircle2 className="w-6 h-6 text-emerald-500" /> : <Circle className="w-6 h-6" />}
                  </button>
                  <input 
                    type="text" placeholder={`Option ${oIndex + 1}`}
                    className={`flex-1 rounded-xl border px-4 py-2.5 ${o.is_correct ? 'bg-emerald-50/80 border-emerald-300 font-medium' : 'bg-white border-slate-200'}`}
                    value={o.text} onChange={e => updateOption(qIndex, oIndex, e.target.value)}
                  />
                  {q.options.length > 2 && (
                    <button onClick={() => removeOption(qIndex, oIndex)} className="text-slate-400 hover:text-red-500 p-1">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={() => addOption(qIndex)} className="mt-2 text-sm text-indigo-600 font-semibold flex items-center gap-1 hover:text-indigo-800">
                <Plus className="w-4 h-4"/> Add Option
              </button>
            </div>
          </div>
        ))}
      </div>
      
      <button onClick={addQuestion} className="w-full py-4 border-2 border-dashed border-slate-300 rounded-2xl text-slate-600 font-semibold hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-all flex items-center justify-center gap-2">
        <Plus className="w-5 h-5"/> Add Another Question
      </button>

    </div>
  );
}
