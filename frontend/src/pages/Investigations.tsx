import { useEffect, useState } from 'react';
import { api } from '../api/client';

const statusColors: Record<string, string> = {
  OPEN: 'bg-blue-100 text-blue-800', UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
  VERIFIED: 'bg-green-100 text-green-800', DISMISSED: 'bg-gray-100 text-gray-800',
  RESOLVED: 'bg-purple-100 text-purple-800',
};
const priorityColors: Record<string, string> = {
  LOW: 'bg-gray-100 text-gray-700', MEDIUM: 'bg-yellow-100 text-yellow-700',
  HIGH: 'bg-orange-100 text-orange-700', URGENT: 'bg-red-100 text-red-700',
};

export default function Investigations() {
  const [cases, setCases] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ member_id: '', title: '', description: '', priority: 'MEDIUM' });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [noteBody, setNoteBody] = useState('');

  const load = () => {
    setLoading(true);
    api.getCases({ page, page_size: 10, status: statusFilter || undefined })
      .then(d => { setCases(d.items); setTotal(d.total); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, [page, statusFilter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.createCase({ member_id: Number(form.member_id), title: form.title, description: form.description || undefined, priority: form.priority });
    setShowForm(false);
    setForm({ member_id: '', title: '', description: '', priority: 'MEDIUM' });
    load();
  };

  const handleStatus = async (caseId: number, newStatus: string) => {
    await api.updateCase(caseId, { status: newStatus });
    load();
  };

  const handleNote = async (caseId: number) => {
    if (!noteBody.trim()) return;
    await api.addNote(caseId, noteBody);
    setNoteBody('');
    const updated = await api.getCases({ page, page_size: 10, status: statusFilter || undefined });
    setCases(updated.items);
  };

  const totalPages = Math.ceil(total / 10);

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Investigation Cases</h1>
        <button onClick={() => setShowForm(!showForm)} className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-primary-700">
          {showForm ? 'Cancel' : '+ New Case'}
        </button>
      </div>
      {showForm && (
        <form onSubmit={handleCreate} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input type="number" placeholder="Member ID" value={form.member_id} onChange={e => setForm({ ...form, member_id: e.target.value })}
              className="border rounded-lg px-3 py-2 text-sm" required />
            <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
              className="border rounded-lg px-3 py-2 text-sm">
              <option value="LOW">Low</option><option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option><option value="URGENT">Urgent</option>
            </select>
          </div>
          <input type="text" placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" required />
          <textarea placeholder="Description (optional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
            className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} />
          <button type="submit" className="bg-primary-600 text-white px-4 py-2 rounded-lg text-sm">Create</button>
        </form>
      )}
      <div className="flex gap-3 mb-4">
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option><option value="UNDER_REVIEW">Under Review</option>
          <option value="VERIFIED">Verified</option><option value="DISMISSED">Dismissed</option>
          <option value="RESOLVED">Resolved</option>
        </select>
        <span className="text-sm text-gray-500 self-center">{total} cases</span>
      </div>
      {loading ? <p className="text-gray-400">Loading...</p> : (
        <div className="space-y-3">
          {cases.map(c => (
            <div key={c.case_id} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{c.title}</h3>
                  <p className="text-xs text-gray-500 mt-1">Member #{c.member_id} {c.mp_name ? `(${c.mp_name})` : ''}</p>
                </div>
                <div className="flex gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[c.status] || ''}`}>{c.status}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${priorityColors[c.priority] || ''}`}>{c.priority}</span>
                </div>
              </div>
              {c.description && <p className="text-sm text-gray-600 mt-2">{c.description}</p>}
              <div className="flex gap-2 mt-3">
                {c.status === 'OPEN' && <button onClick={() => handleStatus(c.case_id, 'UNDER_REVIEW')} className="text-xs bg-yellow-50 text-yellow-700 px-2 py-1 rounded">Start Review</button>}
                {c.status === 'UNDER_REVIEW' && <>
                  <button onClick={() => handleStatus(c.case_id, 'VERIFIED')} className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">Verify</button>
                  <button onClick={() => handleStatus(c.case_id, 'DISMISSED')} className="text-xs bg-gray-50 text-gray-700 px-2 py-1 rounded">Dismiss</button>
                </>}
                {(c.status === 'VERIFIED' || c.status === 'DISMISSED') && <button onClick={() => handleStatus(c.case_id, 'RESOLVED')} className="text-xs bg-purple-50 text-purple-700 px-2 py-1 rounded">Resolve</button>}
                <button onClick={() => setSelected(selected === c.case_id ? null : c.case_id)} className="text-xs text-primary-600 ml-auto">
                  {selected === c.case_id ? 'Hide Notes' : `Notes (${c.notes?.length || 0})`}
                </button>
              </div>
              {selected === c.case_id && (
                <div className="mt-3 border-t pt-3">
                  {c.notes?.map((n: any) => (
                    <div key={n.note_id} className="bg-gray-50 rounded p-2 mb-2 text-sm">
                      <p className="text-xs text-gray-400">User #{n.author_id} — {new Date(n.created_at).toLocaleString()}</p>
                      <p className="mt-1">{n.body}</p>
                    </div>
                  ))}
                  <div className="flex gap-2 mt-2">
                    <input type="text" placeholder="Add a note..." value={noteBody} onChange={e => setNoteBody(e.target.value)}
                      className="flex-1 border rounded px-2 py-1 text-sm" />
                    <button onClick={() => handleNote(c.case_id)} className="bg-primary-600 text-white px-3 py-1 rounded text-sm">Add</button>
                  </div>
                </div>
              )}
            </div>
          ))}
          {cases.length === 0 && <p className="text-gray-400 text-center py-8">No cases found</p>}
          {totalPages > 1 && (
            <div className="flex justify-between items-center">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="text-sm text-primary-600 disabled:text-gray-300">← Prev</button>
              <span className="text-sm text-gray-500">Page {page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="text-sm text-primary-600 disabled:text-gray-300">Next →</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
