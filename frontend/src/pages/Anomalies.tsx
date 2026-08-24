import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

export default function Anomalies() {
  const [scatter, setScatter] = useState<any[]>([]);
  const [dist, setDist] = useState<{ bins: number[]; counts: number[] }>({ bins: [], counts: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getAnomalyScatter(), api.getAnomalyDistribution()])
      .then(([s, d]) => { setScatter(s); setDist(d); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 py-20 text-center">Loading...</p>;

  const anomalies = scatter.filter(s => s.is_anomaly);
  const normal = scatter.filter(s => !s.is_anomaly);

  const scatterChart = {
    tooltip: { formatter: (p: any) => `${p.data?.name || ''}<br/>Ensemble: ${p.value[0]}<br/>Amount: ₹${(p.value[1] / 1e7).toFixed(2)}Cr` },
    legend: { data: ['Normal', 'Anomaly'] },
    xAxis: { name: 'Ensemble Score', type: 'value', max: 1 },
    yAxis: { name: 'Allocated (₹ Cr)', type: 'value' },
    series: [
      { name: 'Normal', type: 'scatter', data: normal.map(s => ({ value: [s.ensemble_score, s.allocated_amount || 0], name: s.mp_name })), symbolSize: 5, itemStyle: { color: '#94a3b8' } },
      { name: 'Anomaly', type: 'scatter', data: anomalies.map(s => ({ value: [s.ensemble_score, s.allocated_amount || 0], name: s.mp_name })), symbolSize: 10, itemStyle: { color: '#ef4444' } },
    ],
    grid: { left: 60, right: 20, bottom: 40 },
  };

  const histChart = {
    xAxis: { type: 'category', data: dist.bins.map(b => b.toFixed(1)), axisLabel: { rotate: 45, fontSize: 9 } },
    yAxis: { type: 'value', name: 'Count' },
    series: [{ type: 'bar', data: dist.counts, itemStyle: { color: '#3b82f6' } }],
    grid: { left: 50, bottom: 80 },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Anomalies</h1>
      <p className="text-sm text-gray-500 mb-6">{anomalies.length} anomalies detected out of {scatter.length} members</p>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Ensemble Score vs Allocation</h3>
          <ReactECharts option={scatterChart} style={{ height: 320 }} />
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Score Distribution</h3>
          <ReactECharts option={histChart} style={{ height: 320 }} />
        </div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-500">MP Name</th>
              <th className="px-4 py-3 font-medium text-gray-500">State</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-right">Ensemble</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-center">Votes</th>
              <th className="px-4 py-3 font-medium text-gray-500 text-right">Risk Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {anomalies.sort((a, b) => b.ensemble_score - a.ensemble_score).slice(0, 50).map(a => (
              <tr key={a.member_id} className="hover:bg-gray-50">
                <td className="px-4 py-3"><Link to={`/projects/${a.member_id}`} className="text-primary-600 hover:underline">{a.mp_name}</Link></td>
                <td className="px-4 py-3 text-gray-600">{a.state}</td>
                <td className="px-4 py-3 text-right font-mono">{a.ensemble_score?.toFixed(3)}</td>
                <td className="px-4 py-3 text-center">{a.risk_level && <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>{a.risk_level}</span>}</td>
                <td className="px-4 py-3 text-right font-mono">{a.risk_score?.toFixed(1) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
