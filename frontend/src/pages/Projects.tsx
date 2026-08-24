import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';

const riskColor: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-red-100 text-red-800',
  CRITICAL: 'bg-purple-100 text-purple-800',
};

export default function Projects() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [states, setStates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const pageSize = 20;

  useEffect(() => { api.getStates().then(setStates); }, []);

  useEffect(() => {
    setLoading(true);
    api.getProjects({ page, page_size: pageSize, search: search || undefined, state: stateFilter || undefined, risk_level: riskFilter || undefined })
      .then(d => { setItems(d.items); setTotal(d.total); })
      .finally(() => setLoading(false));
  }, [page, search, stateFilter, riskFilter]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Projects</h1>
      <div className="flex gap-3 mb-4 flex-wrap">
        <input type="text" placeholder="Search MP or constituency..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-64 focus:ring-2 focus:ring-primary-500 outline-none" />
        <select value={stateFilter} onChange={e => { setStateFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All States</option>
          {states.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={riskFilter} onChange={e => { setRiskFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All Risk Levels</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
        <span className="text-sm text-gray-500 self-center">{total} results</span>
      </div>
      {loading ? <p className="text-gray-400">Loading...</p> : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium text-gray-500">MP Name</th>
                <th className="px-4 py-3 font-medium text-gray-500">State</th>
                <th className="px-4 py-3 font-medium text-gray-500">Constituency</th>
                <th className="px-4 py-3 font-medium text-gray-500 text-right">Allocated</th>
                <th className="px-4 py-3 font-medium text-gray-500 text-right">Risk</th>
                <th className="px-4 py-3 font-medium text-gray-500 text-center">Anomaly</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(p => (
                <tr key={p.member_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/projects/${p.member_id}`} className="text-primary-600 hover:underline font-medium">{p.mp_name}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.state}</td>
                  <td className="px-4 py-3 text-gray-600">{p.constituency}</td>
                  <td className="px-4 py-3 text-right font-mono">{p.allocated_amount != null ? `₹${(p.allocated_amount / 1e7).toFixed(2)}Cr` : '—'}</td>
                  <td className="px-4 py-3 text-right">
                    {p.risk_level && <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${riskColor[p.risk_level] || ''}`}>{p.risk_level} ({p.risk_score})</span>}
                  </td>
                  <td className="px-4 py-3 text-center">{p.is_anomaly ? '⚠️' : '✅'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between items-center px-4 py-3 border-t border-gray-100">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="text-sm text-primary-600 disabled:text-gray-300">← Prev</button>
            <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="text-sm text-primary-600 disabled:text-gray-300">Next →</button>
          </div>
        </div>
      )}
    </div>
  );
}
