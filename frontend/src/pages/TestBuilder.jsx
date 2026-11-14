import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, CheckCircle2, Circle, AlertCircle, Upload, Play, Bot, Sparkles, GitBranch, Brain, Network, ChevronDown, ChevronUp, Link2, FileText, Tag } from 'lucide-react';
import api from '../api/axios';
import PrerequisiteGraph from '../components/PrerequisiteGraph';

export default function TestBuilder() {
  const [title, setTitle] = useState('');
  const [concepts, setConcepts] = useState([]);
  const [conceptGraph, setConceptGraph] = useState({ nodes: [], edges: [] });
  const [showSyllabusGraph, setShowSyllabusGraph] = useState(false);
  const [isInferringGraph, setIsInferringGraph] = useState(false);
  const [graphNotice, setGraphNotice] = useState('');
  const [manualEdgeFrom, setManualEdgeFrom] = useState('');
  const [manualEdgeTo, setManualEdgeTo] = useState('');
  const [isSavingEdge, setIsSavingEdge] = useState(false);
  const [deletingEdgeId, setDeletingEdgeId] = useState(null);
  const [edgeActionError, setEdgeActionError] = useState('');
  const [newConceptName, setNewConceptName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [questions, setQuestions] = useState([
    { text: '', concept_id: '', skill_ids: [], options: [{ text: '', is_correct: true }, { text: '', is_correct: false }] }
  ]);
  const [bulkText, setBulkText] = useState('');
  const [bulkErrors, setBulkErrors] = useState([]);
  const [isParsing, setIsParsing] = useState(false);
  const [isLinkingConcepts, setIsLinkingConcepts] = useState(false);

  // Agentic Curriculum & Self-Correcting DAG State
  const [agentTopic, setAgentTopic] = useState('');
  const [agentNumQs, setAgentNumQs] = useState(4);
  const [agentContext, setAgentContext] = useState('');
  const [showAgentContext, setShowAgentContext] = useState(false);
  const [agentDraft, setAgentDraft] = useState(null);
  const [isAgentDrafting, setIsAgentDrafting] = useState(false);
  const [isAgentApproving, setIsAgentApproving] = useState(false);
  const navigate = useNavigate();

  const fetchConcepts = async () => {
    try {
      const { data } = await api.get('/teacher/concepts');
      setConcepts(data);
      return data;
    } catch (err) {
      if (err.response?.status === 403) {
        setErrorMsg('Forbidden (403): You are logged in with a Student account. Please log out and sign in with a Teacher account to create tests.');
      } else {
        console.error('Failed to fetch concepts', err);
      }
      return null;
    }
  };

  const fetchConceptGraph = async () => {
    try {
      const { data } = await api.get('/concepts/graph');
      setConceptGraph(data || { nodes: [], edges: [] });
    } catch (err) {
      console.warn('Could not fetch syllabus concept graph', err);
    }
  };

  useEffect(() => {
    let active = true;
    const loadInitial = async () => {
      try {
        const [conceptsRes, graphRes] = await Promise.all([
          api.get('/teacher/concepts'),
          api.get('/concepts/graph').catch(() => ({ data: { nodes: [], edges: [] } })),
        ]);
        if (!active) return;
        setConcepts(conceptsRes.data || []);
        setConceptGraph(graphRes.data || { nodes: [], edges: [] });
      } catch (err) {
        if (!active) return;
        if (err.response?.status === 403) {
          setErrorMsg('Forbidden (403): You are logged in with a Student account. Please log out and sign in with a Teacher account to create tests.');
        } else {
          console.error('Failed to load initial builder data', err);
        }
      }
    };
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

  const inferMissingGraphEdges = async () => {
    setIsInferringGraph(true);
    setGraphNotice('');
    setEdgeActionError('');
    try {
      const { data } = await api.post('/concepts/infer-graph');
      setGraphNotice(data?.message || 'Prerequisite links updated.');
      await fetchConceptGraph();
      setShowSyllabusGraph(true);
    } catch (err) {
      setGraphNotice(err.response?.data?.detail || 'Could not infer prerequisite links right now.');
    } finally {
      setIsInferringGraph(false);
    }
  };

  const addManualEdge = async () => {
    setEdgeActionError('');
    setGraphNotice('');
    if (!manualEdgeFrom || !manualEdgeTo) {
      setEdgeActionError('Select both a Prerequisite (From) concept and a Dependent (To) concept.');
      return;
    }
    if (manualEdgeFrom === manualEdgeTo) {
      setEdgeActionError('A concept cannot be a prerequisite of itself.');
      return;
    }
    setIsSavingEdge(true);
    try {
      const { data } = await api.post('/concepts/edges', {
        from_concept_id: Number(manualEdgeFrom),
        to_concept_id: Number(manualEdgeTo),
        confidence: 1.0,
      });
      setManualEdgeFrom('');
      setManualEdgeTo('');
      setGraphNotice(`Added prerequisite link: ${data.from_concept_name} → ${data.to_concept_name}`);
      await fetchConceptGraph();
    } catch (err) {
      setEdgeActionError(err.response?.data?.detail || 'Failed to add prerequisite edge.');
    } finally {
      setIsSavingEdge(false);
    }
  };

  const deleteEdge = async (edgeId) => {
    setEdgeActionError('');
    setGraphNotice('');
    setDeletingEdgeId(edgeId);
    try {
      await api.delete(`/concepts/edges/${edgeId}`);
      setGraphNotice('Removed prerequisite edge from DAG.');
      await fetchConceptGraph();
    } catch (err) {
      setEdgeActionError(err.response?.data?.detail || 'Failed to remove prerequisite edge.');
    } finally {
      setDeletingEdgeId(null);
    }
  };

  const addConcept = async () => {
    if (!newConceptName.trim()) return;
    setErrorMsg('');
    try {
      const { data } = await api.post('/teacher/concepts', { name: newConceptName.trim() });
      setConcepts(prev => (prev.some(c => c.id === data.id) ? prev : [...prev, data]));
      // Auto-link any imported questions waiting on this concept name
      const createdLower = data.name.trim().toLowerCase();
      setQuestions(prevQs =>
        prevQs.map(q => {
          const matchesPending =
            (q.concept_name && q.concept_name.trim().toLowerCase() === createdLower && Number.isNaN(Number(q.concept_id))) ||
            (typeof q.concept_id === 'string' && q.concept_id.trim().toLowerCase() === createdLower);
          return matchesPending
            ? { ...q, concept_id: String(data.id), concept_name: data.name }
            : q;
        })
      );
      setNewConceptName('');
      fetchConceptGraph();
    } catch (err) {
      if (err.response?.status === 403) {
        setErrorMsg('Forbidden (403): Teacher role required to create concepts. Please sign in with a Teacher account.');
      } else {
        setErrorMsg(err.response?.data?.detail || 'Failed to create concept');
      }
    }
  };

  const addQuestion = () => {
    setQuestions([...questions, { text: '', concept_id: '', skill_ids: [], options: [{ text: '', is_correct: true }, { text: '', is_correct: false }] }]);
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
    if (field === 'concept_id') {
      newQs[qIndex].skill_ids = (newQs[qIndex].skill_ids || []).filter(sid => String(sid) !== String(value));
    }
    setQuestions(newQs);
  };

  const toggleSecondarySkill = (qIndex, conceptId) => {
    const cidNum = Number(conceptId);
    if (Number.isNaN(cidNum)) return;
    setQuestions(prev =>
      prev.map((q, idx) => {
        if (idx !== qIndex) return q;
        if (String(q.concept_id) === String(cidNum)) return q;
        const current = q.skill_ids || [];
        const exists = current.includes(cidNum);
        return {
          ...q,
          skill_ids: exists ? current.filter(id => id !== cidNum) : [...current, cidNum]
        };
      })
    );
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
      const cid = parseInt(q.concept_id, 10);
      const secondaryIds = [...new Set(
        (q.skill_ids || [])
          .map(Number)
          .filter(n => !Number.isNaN(n) && n !== cid)
      )];
      return {
        text: q.text.trim(),
        concept_id: Number.isNaN(cid) ? null : cid,
        skill_ids: secondaryIds,
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

  const handleContextFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setAgentContext(String(event.target.result || ''));
      setShowAgentContext(true);
    };
    reader.readAsText(file);
    e.target.value = null;
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
          skill_ids: [],
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

  const missingBulkConcepts = useMemo(() => {
    const existingLower = new Map(
      concepts.map(c => [c.name.trim().toLowerCase(), c])
    );
    const missing = [];
    const seen = new Set();
    questions.forEach(q => {
      const rawId = String(q.concept_id ?? '').trim();
      const rawName = String(q.concept_name ?? '').trim();
      if (rawId && concepts.some(c => String(c.id) === rawId)) return;
      const candidateName = rawName || (rawId && Number.isNaN(Number(rawId)) ? rawId : '');
      if (!candidateName) return;
      const lower = candidateName.toLowerCase();
      if (!existingLower.has(lower) && !seen.has(lower)) {
        seen.add(lower);
        missing.push(candidateName);
      }
    });
    return missing;
  }, [questions, concepts]);

  const createAndLinkMissingConcepts = async () => {
    if (missingBulkConcepts.length === 0) return;
    setErrorMsg('');
    setIsLinkingConcepts(true);
    try {
      for (const name of missingBulkConcepts) {
        await api.post('/teacher/concepts', { name });
      }
      const latest = (await fetchConcepts()) || concepts;
      const byLower = new Map(
        latest.map(c => [c.name.trim().toLowerCase(), c])
      );
      setQuestions(prevQs =>
        prevQs.map(q => {
          const rawId = String(q.concept_id ?? '').trim();
          const rawName = String(q.concept_name ?? '').trim();
          if (rawId && latest.some(c => String(c.id) === rawId)) return q;
          const candidateName = rawName || (rawId && Number.isNaN(Number(rawId)) ? rawId : '');
          const matched = candidateName ? byLower.get(candidateName.toLowerCase()) : null;
          if (!matched) return q;
          return {
            ...q,
            concept_id: String(matched.id),
            concept_name: matched.name,
          };
        })
      );
      setGraphNotice(`Created & linked ${missingBulkConcepts.length} concept(s) into the Knowledge Graph.`);
      await fetchConceptGraph();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to create missing concepts.');
    } finally {
      setIsLinkingConcepts(false);
    }
  };

  const generateCurriculumDraft = async () => {
    if (!agentTopic.trim()) {
      setErrorMsg('Please enter a syllabus topic for the AI Curriculum Agent.');
      return;
    }
    setErrorMsg('');
    setIsAgentDrafting(true);
    try {
      const { data } = await api.post('/agent/teacher/curriculum-draft', {
        topic: agentTopic.trim(),
        num_questions: Number(agentNumQs) || 4,
        difficulty_level: 'Undergraduate',
        syllabus_context: agentContext.trim(),
      });
      setAgentDraft(data);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to generate AI curriculum draft.');
    } finally {
      setIsAgentDrafting(false);
    }
  };

  const updateAgentDraftQuestionText = (qIdx, val) => {
    setAgentDraft(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        draft_questions: prev.draft_questions.map((dq, i) => (i === qIdx ? { ...dq, text: val } : dq)),
      };
    });
  };

  const updateAgentDraftOptionText = (qIdx, oIdx, val) => {
    setAgentDraft(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        draft_questions: prev.draft_questions.map((dq, i) => {
          if (i !== qIdx) return dq;
          return {
            ...dq,
            options: dq.options.map((opt, oi) => (oi === oIdx ? { ...opt, text: val } : opt)),
          };
        }),
      };
    });
  };

  const setAgentDraftCorrectOption = (qIdx, oIdx) => {
    setAgentDraft(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        draft_questions: prev.draft_questions.map((dq, i) => {
          if (i !== qIdx) return dq;
          return {
            ...dq,
            options: dq.options.map((opt, oi) => ({ ...opt, is_correct: oi === oIdx })),
          };
        }),
      };
    });
  };

  const approveDagAndLoadQuestions = async () => {
    if (!agentDraft) return;
    setErrorMsg('');
    setIsAgentApproving(true);
    try {
      const { data } = await api.post('/agent/teacher/curriculum-approve', {
        topic: agentDraft.topic,
        concepts: agentDraft.concepts,
        validated_edges: agentDraft.validated_edges,
        draft_questions: agentDraft.draft_questions,
        create_test: false
      });

      const updatedConcepts = data.all_concepts || concepts;
      setConcepts(updatedConcepts);
      const conceptLookup = {};
      updatedConcepts.forEach(c => {
        conceptLookup[c.name.trim().toLowerCase()] = c.id.toString();
      });

      if (!title.trim()) {
        setTitle(`${agentDraft.topic} — Diagnostic Assessment`);
      }

      const loadedQs = (agentDraft.draft_questions || []).map(dq => {
        const primaryCid = conceptLookup[(dq.concept_name || '').trim().toLowerCase()] || '';
        const secondaryIds = [...new Set(
          (dq.skill_names || [])
            .map(s => Number(conceptLookup[String(s).trim().toLowerCase()]))
            .filter(n => !Number.isNaN(n) && String(n) !== primaryCid)
        )];
        return {
          text: dq.text,
          concept_id: primaryCid,
          concept_name: dq.concept_name,
          skill_ids: secondaryIds,
          options: dq.options.map(o => ({ text: o.text, is_correct: o.is_correct }))
        };
      });

      if (loadedQs.length > 0) {
        if (questions.length === 1 && !questions[0].text && questions[0].options[0].text === '') {
          setQuestions(loadedQs);
        } else {
          setQuestions(prev => [...prev, ...loadedQs]);
        }
      }
      setAgentDraft(null);
      setAgentTopic('');
      setAgentContext('');
      setShowAgentContext(false);
      fetchConceptGraph();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to approve curriculum DAG.');
    } finally {
      setIsAgentApproving(false);
    }
  };

  const syllabusGraphData = useMemo(() => {
    const rawNodes = conceptGraph?.nodes?.length ? conceptGraph.nodes : concepts;
    const nodes = (rawNodes || []).map((c) => ({
      id: String(c.id),
      conceptId: c.id,
      label: c.name,
    }));
    const edges = (conceptGraph?.edges || []).map((e) => ({
      id: `db-${e.id}`,
      from: String(e.from_concept_id),
      to: String(e.to_concept_id),
      confidence: e.confidence ?? 0.85,
      reasoning: e.source ? `Source: ${e.source}` : '',
    }));
    return { nodes, edges };
  }, [conceptGraph, concepts]);

  const agentGraphData = useMemo(() => {
    if (!agentDraft) return { nodes: [], edges: [] };
    const nameMap = new Map();
    const nodes = (agentDraft.concepts || []).map((c) => {
      const id = String(c.name).trim();
      nameMap.set(id.toLowerCase(), id);
      return {
        id,
        conceptId: c.concept_id || null,
        label: id,
        description: c.description || '',
      };
    });

    const edges = (agentDraft.validated_edges || []).map((e, i) => ({
      id: `val-${i}`,
      from: nameMap.get(String(e.from_concept).trim().toLowerCase()) || String(e.from_concept).trim(),
      to: nameMap.get(String(e.to_concept).trim().toLowerCase()) || String(e.to_concept).trim(),
      confidence: 0.92,
      reasoning: e.reasoning || 'Validated DAG dependency',
    }));

    (agentDraft.cycles_resolved || []).forEach((msg, idx) => {
      const m = String(msg).match(/Removed cyclic edge ['"](.+?)\s*->\s*(.+?)['"]/i);
      if (m) {
        const u = nameMap.get(m[1].trim().toLowerCase()) || m[1].trim();
        const v = nameMap.get(m[2].trim().toLowerCase()) || m[2].trim();
        edges.push({
          id: `cyc-${idx}`,
          from: u,
          to: v,
          isRejectedCycle: true,
          reasoning: msg,
        });
      }
    });

    return { nodes, edges };
  }, [agentDraft]);

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

      <div className="glass-panel p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-lg font-semibold text-slate-900">Manage Concepts</h3>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={inferMissingGraphEdges}
              disabled={isInferringGraph || concepts.length < 2}
              className="px-3 py-1.5 rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-700 text-xs font-bold hover:bg-indigo-100 transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isInferringGraph ? 'Inferring Links...' : 'Auto-Infer Prerequisite Links'}
            </button>
            <button
              type="button"
              onClick={() => setShowSyllabusGraph(prev => !prev)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-slate-700 text-xs font-bold hover:bg-slate-50 transition-colors flex items-center gap-1.5"
            >
              <Network className="w-3.5 h-3.5 text-indigo-600" />
              Syllabus Graph ({syllabusGraphData.nodes.length} nodes, {syllabusGraphData.edges.length} edges)
              {showSyllabusGraph ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

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

        {graphNotice && (
          <div className="p-2.5 rounded-xl bg-indigo-50 border border-indigo-200 text-xs font-semibold text-indigo-800">
            {graphNotice}
          </div>
        )}

        {showSyllabusGraph && (
          <div className="space-y-4">
            <PrerequisiteGraph
              nodes={syllabusGraphData.nodes}
              edges={syllabusGraphData.edges}
              mode="curriculum"
              title="Live Syllabus Concept Prerequisite Network"
              subtitle="Complete directed knowledge graph across your syllabus clusters. Node size scales with concept centrality."
              height={420}
            />

            {/* Manual Prerequisite DAG Edge Editor */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                  <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                  Manual Prerequisite Link Editor (NetworkX DAG Guarded)
                </h4>
                <span className="text-[11px] text-slate-500 font-medium">
                  Requires ≥ 2 concepts • Cycles automatically rejected
                </span>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                <select
                  className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"
                  value={manualEdgeFrom}
                  onChange={e => { setManualEdgeFrom(e.target.value); setEdgeActionError(''); }}
                >
                  <option value="">Prerequisite Concept (From)...</option>
                  {concepts.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <span className="text-center font-black text-indigo-600 text-sm px-1">→</span>
                <select
                  className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700"
                  value={manualEdgeTo}
                  onChange={e => { setManualEdgeTo(e.target.value); setEdgeActionError(''); }}
                >
                  <option value="">Dependent Concept (To)...</option>
                  {concepts.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addManualEdge}
                  disabled={isSavingEdge || !manualEdgeFrom || !manualEdgeTo}
                  className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-1.5"
                >
                  <Link2 className="w-3.5 h-3.5" />
                  {isSavingEdge ? 'Checking DAG...' : 'Add Link (DAG Check)'}
                </button>
              </div>

              {edgeActionError && (
                <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs font-semibold text-rose-700">
                  {edgeActionError}
                </div>
              )}

              {(conceptGraph?.edges || []).length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <p className="text-[11px] font-bold text-slate-500">
                    Active Prerequisite Links ({conceptGraph.edges.length})
                  </p>
                  <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
                    {conceptGraph.edges.map(edge => (
                      <div
                        key={edge.id}
                        className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs shadow-2xs"
                      >
                        <span className="font-semibold text-slate-800">
                          {edge.from_concept_name} <span className="text-indigo-600 font-black">→</span> {edge.to_concept_name}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px] font-mono">
                          {edge.source}
                        </span>
                        <button
                          type="button"
                          onClick={() => deleteEdge(edge.id)}
                          disabled={deletingEdgeId === edge.id}
                          title="Delete prerequisite link"
                          className="text-slate-400 hover:text-rose-600 transition-colors disabled:opacity-40"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* AI Curriculum & Self-Correcting DAG Agent */}
      <div className="glass-panel p-6 border border-indigo-200 bg-gradient-to-br from-indigo-50/70 via-white to-slate-50 space-y-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600 text-white">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-900">AI Curriculum & Self-Correcting DAG Agent</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-indigo-100 text-indigo-700">
                  NetworkX + Q-Matrix
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Enter a topic (and optional lecture notes) to extract prerequisite concepts, verify a cycle-free DAG, and draft editable multi-skill MCQs.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowAgentContext(prev => !prev)}
            className="px-3 py-1.5 rounded-xl border border-indigo-200 bg-white text-indigo-700 text-xs font-bold hover:bg-indigo-50 transition-colors flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            {agentContext.trim()
              ? `Syllabus Notes Attached (${agentContext.trim().length} chars)`
              : showAgentContext ? 'Hide Syllabus Notes' : '+ Add Syllabus / Lecture Notes'}
          </button>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="e.g. Thermodynamics & Heat Transfer"
            className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm"
            value={agentTopic}
            onChange={e => setAgentTopic(e.target.value)}
          />
          <select
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-700"
            value={agentNumQs}
            onChange={e => setAgentNumQs(e.target.value)}
          >
            <option value={3}>3 Questions</option>
            <option value={4}>4 Questions</option>
            <option value={5}>5 Questions</option>
            <option value={6}>6 Questions</option>
          </select>
          <button
            onClick={generateCurriculumDraft}
            disabled={isAgentDrafting || !agentTopic.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            {isAgentDrafting ? 'Generating Draft...' : 'Draft Curriculum & MCQs'}
          </button>
        </div>

        {showAgentContext && (
          <div className="p-3.5 rounded-xl bg-white border border-indigo-200 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold text-slate-700">
                Syllabus / Lecture Notes Grounding Context (Optional, max 4000 chars sent)
              </span>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <input
                    type="file"
                    accept=".txt,.md,.csv"
                    onChange={handleContextFileUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <button
                    type="button"
                    className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 text-xs font-semibold hover:bg-slate-100 flex items-center gap-1"
                  >
                    <Upload className="w-3 h-3" /> Load .txt / .md / .csv
                  </button>
                </div>
                {agentContext && (
                  <button
                    type="button"
                    onClick={() => setAgentContext('')}
                    className="text-xs font-semibold text-rose-600 hover:underline"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
            <textarea
              rows={3}
              className="w-full rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2 text-xs text-slate-700 focus:border-indigo-500"
              placeholder="Paste syllabus objectives, lecture outline, or key definitions to constrain concept extraction and MCQ wording..."
              value={agentContext}
              onChange={e => setAgentContext(e.target.value)}
            />
          </div>
        )}

        {agentDraft && (
          <div className="space-y-4 pt-4 border-t border-indigo-100">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-mono font-bold text-slate-600">
                Engine: {agentDraft.engine_mode} • Topological Order: {agentDraft.topological_order?.join(' → ')}
              </span>
              <button
                onClick={approveDagAndLoadQuestions}
                disabled={isAgentApproving}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black uppercase tracking-wider disabled:opacity-50"
              >
                {isAgentApproving ? 'Saving DAG...' : 'Approve DAG & Load Questions into Builder'}
              </button>
            </div>

            {agentDraft.cycles_resolved?.length > 0 && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 font-semibold">
                Self-Correction Applied: {agentDraft.cycles_resolved.join(' | ')}
              </div>
            )}

            {/* Visual Directed Network Graph of Proposed & Self-Corrected DAG */}
            <PrerequisiteGraph
              nodes={agentGraphData.nodes}
              edges={agentGraphData.edges}
              mode="curriculum"
              title="Curriculum Prerequisite Network Graph (NetworkX Verified DAG)"
              subtitle="Interactive directed node-edge graph showing concept dependencies and any circular arcs pruned by NetworkX."
              height={360}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-2">
                <p className="text-xs font-black uppercase text-slate-500 flex items-center gap-1.5">
                  <GitBranch className="w-3.5 h-3.5 text-indigo-600" />
                  Validated Prerequisite Edges ({agentDraft.validated_edges?.length || 0})
                </p>
                <ul className="text-xs text-slate-700 space-y-1">
                  {agentDraft.validated_edges?.map((e, i) => (
                    <li key={i} className="font-medium">
                      {e.from_concept} <span className="text-indigo-600 font-bold">→</span> {e.to_concept}
                      {e.reasoning && <span className="text-slate-400 text-[11px] block pl-2">{e.reasoning}</span>}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900 text-slate-100 space-y-1.5 font-mono text-[11px]">
                <p className="text-indigo-300 font-bold flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5" /> Agent Reasoning Trace
                </p>
                {agentDraft.reasoning_trace?.map(st => (
                  <p key={st.step} className="text-slate-300">
                    [{st.step}] {st.tool_name}: {st.observation}
                  </p>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-xs font-black uppercase text-slate-500">
                Drafted Q-Matrix Questions ({agentDraft.draft_questions?.length || 0}) — Editable Before Approval
              </p>
              {agentDraft.draft_questions?.map((dq, i) => (
                <div key={i} className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-black text-indigo-700">Q{i + 1} (Editable Draft)</span>
                    <span className="text-indigo-600 font-semibold">
                      Skills: {dq.skill_names?.join(', ')}
                    </span>
                  </div>
                  <input
                    type="text"
                    value={dq.text}
                    onChange={e => updateAgentDraftQuestionText(i, e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2 font-semibold text-slate-800 focus:border-indigo-500"
                  />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {(dq.options || []).map((opt, oi) => (
                      <div key={oi} className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => setAgentDraftCorrectOption(i, oi)}
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
                          onChange={e => updateAgentDraftOptionText(i, oi, e.target.value)}
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
        )}
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

      {missingBulkConcepts.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-300 text-amber-900 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="text-xs font-black uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              {missingBulkConcepts.length} Unsaved Concept Tag(s) Detected
            </div>
            <p className="text-xs text-amber-800">
              Missing from Knowledge Graph: <strong>{missingBulkConcepts.join(', ')}</strong>. Link them before saving so DINA &amp; Q-Matrix inference stay accurate.
            </p>
          </div>
          <button
            type="button"
            onClick={createAndLinkMissingConcepts}
            disabled={isLinkingConcepts}
            className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-black uppercase tracking-wider whitespace-nowrap disabled:opacity-50 flex items-center gap-1.5 self-start sm:self-center"
          >
            <Link2 className="w-3.5 h-3.5" />
            {isLinkingConcepts ? 'Linking Concepts...' : 'Create & Link Missing Concepts'}
          </button>
        </div>
      )}

      <div className="space-y-6">
        {questions.map((q, qIndex) => {
          const primaryIdStr = String(q.concept_id ?? '');
          const secondarySkillIds = (q.skill_ids || []).filter(sid => String(sid) !== primaryIdStr);
          const hasPrimaryNumeric = primaryIdStr && concepts.some(c => String(c.id) === primaryIdStr);
          const totalSkills = (hasPrimaryNumeric ? 1 : 0) + secondarySkillIds.length;
          return (
          <div key={qIndex} className="glass-panel p-6 border-l-4 border-indigo-500 relative">
            <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-slate-800 text-lg">Question {qIndex + 1}</h3>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                  totalSkills > 0 ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  Q-Matrix: {totalSkills} skill{totalSkills === 1 ? '' : 's'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <select 
                  className="rounded-xl border-slate-200 text-sm bg-white px-3 py-1.5 focus:border-indigo-500 max-w-[220px] truncate"
                  value={q.concept_id} onChange={e => updateQuestion(qIndex, 'concept_id', e.target.value)}
                >
                  <option value="">Select Primary Concept (Optional)...</option>
                  {concepts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  {q.concept_name && !concepts.some(c => String(c.id) === primaryIdStr) && (
                    <option value={q.concept_id || q.concept_name}>{q.concept_name} (Unsaved)</option>
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
              className="w-full rounded-xl border border-slate-200 bg-white/80 px-4 py-3 mb-4 focus:border-indigo-500"
              value={q.text} onChange={e => updateQuestion(qIndex, 'text', e.target.value)}
            />

            {/* Multi-Skill Q-Matrix Secondary Tag Selector */}
            {concepts.length > 0 && (
              <div className="mb-5 p-3 rounded-xl bg-slate-50/90 border border-slate-200 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] font-black uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-indigo-600" />
                    Multi-Skill Q-Matrix Tags (Click to toggle secondary skills)
                  </span>
                  <span className="text-[10px] text-slate-500 font-semibold">
                    {secondarySkillIds.length > 0
                      ? `${secondarySkillIds.length} secondary skill(s) pinned (auto-infer skipped)`
                      : 'Optional: click chips to bind multiple concepts'}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto pr-1">
                  {concepts.map(c => {
                    const isPrimary = String(c.id) === primaryIdStr;
                    const isSecondary = !isPrimary && secondarySkillIds.includes(c.id);
                    return (
                      <button
                        type="button"
                        key={c.id}
                        disabled={isPrimary}
                        onClick={() => toggleSecondarySkill(qIndex, c.id)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-colors ${
                          isPrimary
                            ? 'bg-indigo-600 text-white border-indigo-600 cursor-default'
                            : isSecondary
                            ? 'bg-purple-100 text-purple-800 border-purple-300'
                            : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
                        }`}
                      >
                        {isPrimary ? `★ ${c.name} (Primary)` : isSecondary ? `✓ ${c.name}` : `+ ${c.name}`}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

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
          );
        })}
      </div>
      
      <button onClick={addQuestion} className="w-full py-4 border-2 border-dashed border-slate-300 rounded-2xl text-slate-600 font-semibold hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50/50 transition-all flex items-center justify-center gap-2">
        <Plus className="w-5 h-5"/> Add Another Question
      </button>

    </div>
  );
}
