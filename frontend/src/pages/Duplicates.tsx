import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

export default function Duplicates() {
  const [summary, setSummary] = useState<any>(null);
  const [pairs, setPairs] = useState<any[]>([]);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.getDuplicateSummary().then(setSummary); }, []);

  useEffect(() => {
    setLoading(true);
    api.getDuplicates({ flagged_only: flaggedOnly, page_size: 50 })
      .then(d => setPairs(d.items))
      .finally(() => setLoading(false));
  }, [flaggedOnly]);

  const simChart = summary ? {
    xAxis: { type: 'category', data: ['Total Pairs', 'Flagged', 'Max Similarity (%)', 'Mean Similarity (%)'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: [summary.total_pairs, summary.flagged_pairs, summary.max_similarity * 100, summary.mean_similarity * 100], itemStyle: { color: '#3b82f6' } }],
    grid: { left: 50, bottom: 30 },
  } : null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Duplicate Detection</h1>
      <p className="text-sm text-gray-500 mb-6">TF-IDF char n-grams + token Jaccard + constituency similarity</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {summary && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Summary</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500">Total Pairs</p><p className="text-xl font-bold">{summary.total_pairs}</p></div>
              <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500">Flagged</p><p className="text-xl font-bold text-red-600">{summary.flagged_pairs}</p></div>
              <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500">Max Similarity</p><p className="text-xl font-bold">{(summary.max_similarity * 100).toFixed(1)}%</p></div>
              <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500">Mean Similarity</p><p className="text-xl font-bold">{(summary.mean_similarity * 100).toFixed(1)}%</p></div>
            </div>
          </div>
        )}
        {simChart && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Similarity Overview</h3>
            <ReactECharts option={simChart} style={{ height: 220 }} />
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 mb-4">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={flaggedOnly} onChange={e => setFlaggedOnly(e.target.checked)}
            className="rounded border-gray-300" />
          Show flagged only
        </label>
        <span className="text-sm text-gray-500">{pairs.length} pairs shown</span>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-500">MP A</th>
              <th className="px-4 py-3 font-medium text-gray-500">MP B</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-right">Name Sim</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-right">Const Sim</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-right">Overall</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-center">Flagged</th>
              <th className="px-4 py-3 font-medium text-gray-500">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {pairs.map((p, i) => (
              <tr key={i} className={`hover:bg-gray-50 ${p.potential_duplicate ? 'bg-red-50' : ''}`}>
                <td className="px-4 py-3"><Link to={`/projects/${p.member_id_a}`} className="text-primary-600 hover:underline">{p.mp_name_a}</Link></td>
                <td className="px-4 py-3"><Link to={`/projects/${p.member_id_b}`} className="text-primary-600 hover:underline">{p.mp_name_b}</Link></td>
                <td className="px-4 py-3 text-right font-mono">{(p.name_similarity * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-right font-mono">{(p.constituency_similarity * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-right font-mono font-bold">{(p.overall_similarity * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-center">{p.potential_duplicate ? '🚩' : '—'}</td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{p.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
