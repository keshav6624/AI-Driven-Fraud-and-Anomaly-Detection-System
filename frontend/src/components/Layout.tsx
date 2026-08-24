import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const nav = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/projects', label: 'Projects', icon: '📋' },
  { to: '/risk', label: 'Risk', icon: '⚠️' },
  { to: '/anomalies', label: 'Anomalies', icon: '🔍' },
  { to: '/duplicates', label: 'Duplicates', icon: '👥' },
  { to: '/map', label: 'Map', icon: '🗺️' },
  { to: '/investigations', label: 'Cases', icon: '📁' },
  { to: '/assistant', label: 'AI Assistant', icon: '🤖' },
  { to: '/scoring', label: 'ML Scoring', icon: '🧮' },
  { to: '/admin', label: 'Admin', icon: '⚙️' },
  { to: '/about', label: 'About', icon: 'ℹ️' },
];

export default function Layout() {
  const { pathname } = useLocation();
  const { username, role, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-gray-900 text-gray-100 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-700">
          <h1 className="text-lg font-bold tracking-tight">MPLAD-Sentinel</h1>
          <p className="text-xs text-gray-400 mt-0.5">MP Local Area Development Monitor</p>
        </div>
        <nav className="flex-1 py-2 overflow-y-auto">
          {nav.map(n => (
            <Link key={n.to} to={n.to}
              className={`flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
                pathname === n.to ? 'bg-primary-600 text-white' : 'text-gray-300 hover:bg-gray-800'
              }`}>
              <span>{n.icon}</span> {n.label}
            </Link>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-gray-700 text-xs">
          <div className="text-gray-400">{username} <span className="text-gray-500">({role})</span></div>
          <button onClick={handleLogout} className="mt-1 text-red-400 hover:text-red-300">Logout</button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-gray-50">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
