import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import TeacherDashboard from './pages/TeacherDashboard';
import StudentDashboard from './pages/StudentDashboard';
import DiagnosticReport from './pages/DiagnosticReport';
import TestBuilder from './pages/TestBuilder';
import TakeTest from './pages/TakeTest';
import TestResults from './pages/TestResults';
import { LogOut, GraduationCap, UserCheck } from 'lucide-react';

const ProtectedRoute = ({ children, allowedRole }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRole && user.role !== allowedRole) {
    return <Navigate to={user.role === 'teacher' ? '/teacher' : '/student'} replace />;
  }
  return children;
};

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="glass-panel sticky top-0 z-50 rounded-none border-t-0 border-x-0 bg-white/90 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600">
                KnowledgeTrace MCQ
              </span>
            </div>
            <div className="flex items-center space-x-4">
              {user && (
                <>
                  <div className="flex items-center gap-3 bg-slate-100/80 px-3.5 py-1.5 rounded-full border border-slate-200">
                    <span className="text-sm font-semibold text-slate-800">
                      {user.name || user.email}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1 ${
                      user.role === 'teacher' 
                        ? 'bg-indigo-600 text-white shadow-xs' 
                        : 'bg-emerald-600 text-white shadow-xs'
                    }`}>
                      {user.role === 'teacher' ? <UserCheck className="w-3.5 h-3.5" /> : <GraduationCap className="w-3.5 h-3.5" />}
                      {user.role}
                    </span>
                  </div>
                  <button 
                    onClick={logout} 
                    title="Sign Out"
                    className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors"
                  >
                    <LogOut className="h-5 w-5" />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main className="flex-1 w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        {children}
      </main>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Teacher Routes */}
            <Route path="/teacher" element={<ProtectedRoute allowedRole="teacher"><TeacherDashboard /></ProtectedRoute>} />
            <Route path="/teacher/create-test" element={<ProtectedRoute allowedRole="teacher"><TestBuilder /></ProtectedRoute>} />
            <Route path="/teacher/test/:id/results" element={<ProtectedRoute allowedRole="teacher"><TestResults /></ProtectedRoute>} />
            
            {/* Student Routes */}
            <Route path="/student" element={<ProtectedRoute allowedRole="student"><StudentDashboard /></ProtectedRoute>} />
            <Route path="/student/take-test/:id" element={<ProtectedRoute allowedRole="student"><TakeTest /></ProtectedRoute>} />
            <Route path="/student/diagnosis" element={<ProtectedRoute allowedRole="student"><DiagnosticReport /></ProtectedRoute>} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  );
}
