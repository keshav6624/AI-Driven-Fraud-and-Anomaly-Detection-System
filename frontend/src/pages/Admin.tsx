import { useAuth } from '../contexts/AuthContext';

export default function Admin() {
  const { role } = useAuth();
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Admin</h1>
      {role !== 'ADMIN' ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-yellow-800">
          You need ADMIN role to access this page.
        </div>
      ) : (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold mb-3">User Management</h2>
          <p className="text-sm text-gray-500 mb-4">Create and manage platform users via the API or CLI.</p>
          <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm">
            <p className="text-gray-500"># Create a user via API:</p>
            <p className="text-primary-600">POST /auth/users</p>
            <p className="text-gray-400 mt-2">{'{ "username": "...", "password": "...", "full_name": "...", "role": "ANALYST" }'}</p>
          </div>
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Roles</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li><strong>ADMIN</strong> — Full access, user management</li>
              <li><strong>ANALYST</strong> — View data, create investigation cases</li>
              <li><strong>INVESTIGATOR</strong> — Manage investigation cases and notes</li>
              <li><strong>VIEWER</strong> — Read-only access to dashboards</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
