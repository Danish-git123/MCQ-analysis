import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { UserCheck, GraduationCap, Lock, Mail, ArrowRight } from 'lucide-react';

export default function Login() {
  const [selectedRole, setSelectedRole] = useState('teacher'); // 'teacher' or 'student'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [infoMsg, setInfoMsg] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setInfoMsg('');
    try {
      const userData = await login(email, password);
      if (userData.role !== selectedRole) {
        setInfoMsg(`Account is registered as a ${userData.role.toUpperCase()}. Redirecting to ${userData.role} dashboard...`);
        setTimeout(() => {
          if (userData.role === 'teacher') navigate('/teacher');
          else navigate('/student');
        }, 1200);
      } else {
        if (userData.role === 'teacher') navigate('/teacher');
        else navigate('/student');
      }
    } catch (err) {
      setError('Invalid email or password. Please try again.');
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-6">
      <div className="glass-panel p-8 w-full max-w-md shadow-xl border border-slate-200/80">
        <h2 className="text-3xl font-extrabold text-center text-slate-900 tracking-tight mb-2">
          Portal Login
        </h2>
        <p className="text-center text-slate-500 text-sm mb-6">
          Select your role and sign in to continue
        </p>

        {/* Role Toggle Tabs */}
        <div className="grid grid-cols-2 gap-2 p-1.5 bg-slate-100/90 rounded-2xl mb-6 border border-slate-200">
          <button
            type="button"
            onClick={() => { setSelectedRole('teacher'); setError(''); setInfoMsg(''); }}
            className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              selectedRole === 'teacher'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            <UserCheck className="w-4 h-4" />
            Teacher Role
          </button>
          <button
            type="button"
            onClick={() => { setSelectedRole('student'); setError(''); setInfoMsg(''); }}
            className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              selectedRole === 'student'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            <GraduationCap className="w-4 h-4" />
            Student Role
          </button>
        </div>

        {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm font-medium">{error}</div>}
        {infoMsg && <div className="mb-4 p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-sm font-medium">{infoMsg}</div>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="h-5 w-5" />
              </div>
              <input
                type="email"
                required
                placeholder="name@example.com"
                className="pl-10 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1.5">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="h-5 w-5" />
              </div>
              <input
                type="password"
                required
                placeholder="••••••••"
                className="pl-10 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl shadow-md text-sm font-bold text-white transition-all ${
              selectedRole === 'teacher'
                ? 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200'
                : 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200'
            }`}
          >
            Sign In as {selectedRole === 'teacher' ? 'Teacher' : 'Student'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-600">
          Don't have an account?{' '}
          <Link to="/register" className="font-semibold text-indigo-600 hover:text-indigo-500">
            Register Here
          </Link>
        </div>
      </div>
    </div>
  );
}
