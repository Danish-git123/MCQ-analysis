import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Users, BarChart3, BookOpen, Check, Search, X, UserCheck, ShieldCheck, Mail, AlertCircle } from 'lucide-react';
import api from '../api/axios';

export default function TeacherDashboard() {
  const [tests, setTests] = useState([]);
  const [assignModalTest, setAssignModalTest] = useState(null);
  const [students, setStudents] = useState([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [enrollEmail, setEnrollEmail] = useState('');
  const [enrollError, setEnrollError] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [successToast, setSuccessToast] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchTests();
  }, []);

  const fetchTests = async () => {
    try {
      const { data } = await api.get('/teacher/tests');
      setTests(data);
    } catch (e) {
      console.error('Failed to fetch tests', e);
    }
  };

  const openAssignModal = async (test) => {
    setAssignModalTest(test);
    setSelectedStudentIds([]);
    setSearchQuery('');
    setEnrollEmail('');
    setEnrollError('');
    try {
      const { data } = await api.get('/teacher/students');
      setStudents(data);
      if (test.assignments) {
        const alreadyAssigned = test.assignments.map(a => a.student_id);
        setSelectedStudentIds(alreadyAssigned);
      }
    } catch (e) {
      console.error('Failed to fetch students', e);
    }
  };

  const closeAssignModal = () => {
    setAssignModalTest(null);
    setStudents([]);
    setSelectedStudentIds([]);
    setEnrollEmail('');
    setEnrollError('');
  };

  const toggleStudent = (id) => {
    if (selectedStudentIds.includes(id)) {
      setSelectedStudentIds(selectedStudentIds.filter(sid => sid !== id));
    } else {
      setSelectedStudentIds([...selectedStudentIds, id]);
    }
  };

  const toggleSelectAll = () => {
    const filtered = filteredStudents.map(s => s.id);
    const allFilteredSelected = filtered.every(id => selectedStudentIds.includes(id));
    if (allFilteredSelected) {
      setSelectedStudentIds(selectedStudentIds.filter(id => !filtered.includes(id)));
    } else {
      const combined = new Set([...selectedStudentIds, ...filtered]);
      setSelectedStudentIds(Array.from(combined));
    }
  };

  const handleAssignSubmit = async () => {
    if (!assignModalTest) return;
    setAssigning(true);
    setEnrollError('');
    try {
      await api.post('/teacher/assign-test', {
        test_id: assignModalTest.id,
        student_ids: selectedStudentIds
      });
      setSuccessToast(`Test "${assignModalTest.title}" assigned to ${selectedStudentIds.length} student(s)!`);
      setTimeout(() => setSuccessToast(''), 4000);
      closeAssignModal();
      fetchTests();
    } catch (e) {
      setEnrollError(e.response?.data?.detail || 'Failed to assign test');
    } finally {
      setAssigning(false);
    }
  };

  const handleEnrollByEmail = async (e) => {
    e.preventDefault();
    if (!enrollEmail.trim() || !assignModalTest) return;
    setEnrollError('');
    setAssigning(true);
    try {
      await api.post('/teacher/assign-test', {
        test_id: assignModalTest.id,
        student_emails: [enrollEmail.trim()]
      });
      setSuccessToast(`Successfully enrolled and assigned test to "${enrollEmail.trim()}"!`);
      setTimeout(() => setSuccessToast(''), 4000);
      setEnrollEmail('');
      await fetchTests();
      
      // Refresh students roster
      const { data } = await api.get('/teacher/students');
      setStudents(data);
      const updatedTest = tests.find(t => t.id === assignModalTest.id);
      if (updatedTest && updatedTest.assignments) {
        setSelectedStudentIds(updatedTest.assignments.map(a => a.student_id));
      }
    } catch (err) {
      setEnrollError(err.response?.data?.detail || 'Failed to enroll student email.');
    } finally {
      setAssigning(false);
    }
  };

  const filteredStudents = students.filter(s => 
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-8 pb-12">
      {/* Top Banner & Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Teacher Dashboard</h1>
          <p className="text-slate-500 mt-1">Manage your tests, enroll students via email, and track progress</p>
        </div>
        <button 
          onClick={() => navigate('/teacher/create-test')}
          className="inline-flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl hover:bg-indigo-700 transition-all shadow-md font-semibold"
        >
          <Plus className="w-5 h-5" />
          Create New Test
        </button>
      </div>

      {/* Toast Banner */}
      {successToast && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl font-semibold flex items-center gap-3 shadow-sm animate-fade-in">
          <ShieldCheck className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Test Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tests.map(test => {
          const assignedCount = test.assignments ? test.assignments.length : 0;
          return (
            <div key={test.id} className="glass-panel p-6 flex flex-col transition-all hover:-translate-y-1 hover:shadow-xl border border-slate-200/80">
              <div className="flex items-center gap-3.5 mb-4">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                  <BookOpen className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-800 line-clamp-1">{test.title}</h3>
              </div>
              
              <div className="mt-auto space-y-4 pt-4 border-t border-slate-100">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
                  <span className="flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-lg">
                    <BookOpen className="w-3.5 h-3.5"/> {test.questions.length} Questions
                  </span>
                  <span className="flex items-center gap-1.5 bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-lg">
                    <Users className="w-3.5 h-3.5"/> {assignedCount} Enrolled Student{assignedCount !== 1 ? 's' : ''}
                  </span>
                </div>

                <div className="flex gap-2.5">
                  <button 
                    onClick={() => navigate(`/teacher/test/${test.id}/results`)}
                    className="flex-1 bg-white border border-slate-200 text-slate-700 px-4 py-2.5 rounded-xl hover:bg-slate-50 font-semibold inline-flex items-center justify-center gap-2 transition-colors text-sm shadow-xs"
                  >
                    <BarChart3 className="w-4 h-4"/> Results
                  </button>

                  <button 
                    onClick={() => openAssignModal(test)}
                    className="flex-1 bg-indigo-600 text-white px-4 py-2.5 rounded-xl hover:bg-indigo-700 font-semibold inline-flex items-center justify-center gap-2 transition-colors text-sm shadow-sm"
                  >
                    <Users className="w-4 h-4"/> Enroll / Assign
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {tests.length === 0 && (
          <div className="col-span-full py-16 text-center text-slate-500 bg-white/60 rounded-3xl border border-dashed border-slate-300 shadow-xs">
            <BookOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" />
            <h3 className="text-lg font-bold text-slate-700 mb-1">No Tests Created Yet</h3>
            <p className="text-sm text-slate-500 mb-4">Click "Create New Test" to build MCQs and assign them to students.</p>
            <button 
              onClick={() => navigate('/teacher/create-test')}
              className="inline-flex items-center gap-2 bg-indigo-600 text-white px-5 py-2 rounded-xl hover:bg-indigo-700 text-sm font-semibold"
            >
              <Plus className="w-4 h-4" /> Create Test Now
            </button>
          </div>
        )}
      </div>

      {/* Enroll & Assign Students Modal */}
      {assignModalTest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="glass-panel w-full max-w-xl bg-white p-6 rounded-3xl shadow-2xl border border-slate-100 flex flex-col max-h-[90vh]">
            
            {/* Modal Header */}
            <div className="flex justify-between items-start mb-4 pb-3 border-b border-slate-100">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  Enroll & Assign Students
                </h2>
                <p className="text-xs font-semibold text-indigo-600 mt-0.5">
                  Test: {assignModalTest.title}
                </p>
              </div>
              <button 
                onClick={closeAssignModal}
                className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error Banner inside modal */}
            {enrollError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{enrollError}</span>
              </div>
            )}

            {/* Form 1: Enroll Student directly via Email */}
            <form onSubmit={handleEnrollByEmail} className="mb-5 p-4 bg-indigo-50/50 rounded-2xl border border-indigo-100 space-y-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-indigo-900">
                Enroll Student by Email ID
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Mail className="w-4 h-4 text-indigo-400 absolute left-3 top-3" />
                  <input 
                    type="email"
                    required
                    placeholder="student@gmail.com"
                    className="w-full pl-9 pr-3 py-2 rounded-xl border border-indigo-200 bg-white text-sm focus:border-indigo-500 font-medium"
                    value={enrollEmail}
                    onChange={e => setEnrollEmail(e.target.value)}
                  />
                </div>
                <button 
                  type="submit"
                  disabled={assigning || !enrollEmail.trim()}
                  className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-indigo-700 transition-colors disabled:opacity-50 flex-shrink-0 shadow-sm"
                >
                  Enroll & Assign
                </button>
              </div>
            </form>

            <div className="relative flex items-center mb-3">
              <div className="flex-grow border-t border-slate-200"></div>
              <span className="flex-shrink mx-3 text-xs font-bold text-slate-400 uppercase tracking-wider">Or Select Registered Students</span>
              <div className="flex-grow border-t border-slate-200"></div>
            </div>

            {/* Search Bar for registered students */}
            <div className="space-y-2 mb-3">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-2.5" />
                <input 
                  type="text"
                  placeholder="Filter student list..."
                  className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-xs focus:border-indigo-500 focus:bg-white transition-all"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>

              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-500">
                  {selectedStudentIds.length} student(s) selected
                </span>
                <button 
                  type="button"
                  onClick={toggleSelectAll}
                  className="text-indigo-600 hover:text-indigo-800 underline"
                >
                  {filteredStudents.every(s => selectedStudentIds.includes(s.id)) ? 'Deselect All' : 'Select All Filtered'}
                </button>
              </div>
            </div>

            {/* Roster Scroll Box */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1 my-1">
              {filteredStudents.map(student => {
                const isSelected = selectedStudentIds.includes(student.id);
                return (
                  <div
                    key={student.id}
                    onClick={() => toggleStudent(student.id)}
                    className={`flex items-center justify-between p-3 rounded-2xl border cursor-pointer transition-all ${
                      isSelected 
                        ? 'border-indigo-500 bg-indigo-50/70 shadow-xs' 
                        : 'border-slate-200/80 bg-white hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700'
                      }`}>
                        {student.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-800">{student.name}</p>
                        <p className="text-xs text-slate-500">{student.email}</p>
                      </div>
                    </div>

                    <div className={`w-6 h-6 rounded-lg border flex items-center justify-center transition-all ${
                      isSelected ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 bg-white'
                    }`}>
                      {isSelected && <Check className="w-4 h-4" />}
                    </div>
                  </div>
                );
              })}

              {filteredStudents.length === 0 && (
                <div className="text-center py-6 text-slate-400 text-xs">
                  {students.length === 0 ? 'No registered students found.' : 'No matching students.'}
                </div>
              )}
            </div>

            {/* Modal Actions Footer */}
            <div className="flex gap-3 pt-4 border-t border-slate-100 mt-2">
              <button 
                type="button"
                onClick={closeAssignModal}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors"
              >
                Close
              </button>
              <button 
                type="button"
                onClick={handleAssignSubmit}
                disabled={assigning || selectedStudentIds.length === 0}
                className="flex-1 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-bold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md inline-flex items-center justify-center gap-2"
              >
                <UserCheck className="w-4 h-4" />
                {assigning ? 'Assigning...' : `Assign Selected (${selectedStudentIds.length})`}
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
