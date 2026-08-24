import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

const riskColor: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800', MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-red-100 text-red-800', CRITICAL: 'bg-purple-100 text-purple-800',
};

export default function Scoring() {
  const [form, setForm] = useState({ mp_name: '', state: '', constituency: '', allocated_amount: '' });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [batchResult, setBatchResult] = useState<any>(null);
  const [batchLoading, setBatchLoading] = useState(false);

  const handleScore = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await api.scoreMember({
        mp_name: form.mp_name,
        state: form.state.toUpperCase(),
        constituency: form.constituency,
        allocated_amount: form.allocated_amount ? Number(form.allocated_amount) : null,
      });
      setResult(res);
    } catch (err: any) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleBatch = async () => {
    setBatchLoading(true);
    setBatchResult(null);
    try {
      const res = await api.runBatchInference();
      setBatchResult(res);
    } catch (err: any) {
      setBatchResult({ error: err.message });
    } finally {
      setBatchLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Real-time ML Scoring</h1>
      <p className="text-sm text-gray-500 mb-6">Run the AI/ML pipeline on-demand for any MP allocation</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Single scoring form */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold mb-4">Score a Single MP</h2>
          <form onSubmit={handleScore} className="space-y-3">
            <input type="text" placeholder="MP Name" value={form.mp_name} onChange={e => setForm({ ...form, mp_name: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm" required />
            <input type="text" placeholder="State (e.g., MAHARASHTRA)" value={form.state} onChange={e => setForm({ ...form, state: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm" required />
            <input type="text" placeholder="Constituency" value={form.constituency} onChange={e => setForm({ ...form, constituency: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm" required />
            <input type="number" placeholder="Allocated Amount (₹)" value={form.allocated_amount} onChange={e => setForm({ ...form, allocated_amount: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm" min="0" step="0.01" />
            <button type="submit" disabled={loading}
              className="w-full bg-primary-600 text-white py-2.5 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50">
              {loading ? 'Running ML Pipeline...' : 'Run AI Scoring'}
            </button>
          </form>
        </div>

        {/* Batch inference */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h2 className="text-lg font-semibold mb-4">Batch Inference</h2>
          <p className="text-sm text-gray-500 mb-4">Re-run the full ML pipeline on all 543 MPs</p>
          <button onClick={handleBatch} disabled={batchLoading}
            className="bg-gray-900 text-white px-4 py-2.5 rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50">
            {batchLoading ? 'Running Pipeline...' : 'Run Full Pipeline'}
          </button>
          {batchResult && !batchResult.error && (
            <div className="mt-4 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Members Processed</p>
                  <p className="text-xl font-bold">{batchResult.members_processed}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500">Anomalies Detected</p>
                  <p className="text-xl font-bold text-red-600">{batchResult.anomalies_detected}</p>
                </div>
              </div>
              <p className="text-xs text-gray-400">Model version: {batchResult.model_version}</p>
            </div>
          )}
        </div>
      </div>

      {/* Single result */}
      {result && !result.error && (
        <div className="mt-6 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h2 className="text-xl font-bold">{result.mp_name}</h2>
              <p className="text-gray-500">{result.constituency}, {result.state}</p>
            </div>
            <div className="flex gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${riskColor[result.risk_level] || ''}`}>
                {result.risk_level} Risk
              </span>
              {result.is_anomaly && <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">Anomaly</span>}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Risk Score</p>
              <p className="text-2xl font-bold">{result.risk_score}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Ensemble Score</p>
              <p className="text-2xl font-bold">{result.ensemble_score?.toFixed(3)}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Anomaly Votes</p>
              <p className="text-2xl font-bold">{result.anomaly_votes}/3</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500">Escalated</p>
              <p className="text-2xl font-bold">{result.risk_escalated ? 'Yes' : 'No'}</p>
            </div>
          </div>

          {/* Risk gauge */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <ReactECharts option={{
                series: [{
                  type: 'gauge', min: 0, max: 100,
                  detail: { formatter: '{value}', fontSize: 24 },
                  data: [{ value: result.risk_score, name: 'Risk Score' }],
                  axisLine: { lineStyle: { width: 15, color: [[0.25, '#22c55e'], [0.45, '#f59e0b'], [0.65, '#ef4444'], [1, '#7c3aed']] } },
                }],
              }} style={{ height: 250 }} />
            </div>
            <div>
              <ReactECharts option={{
                radar: {
                  indicator: [
                    { name: 'Financial', max: 100 }, { name: 'Data Quality', max: 100 },
                    { name: 'Duplicate', max: 100 }, { name: 'Interest', max: 100 },
                  ],
                },
                series: [{ type: 'radar', data: [{ value: [
                  result.risk_components?.financial || 0,
                  result.risk_components?.data_quality || 0,
                  result.risk_components?.duplicate || 0,
                  result.risk_components?.interest || 0,
                ], name: 'Risk Components' }] }],
              }} style={{ height: 250 }} />
            </div>
          </div>

          {/* Anomaly details */}
          {result.anomaly_reasons?.length > 0 && (
            <div className="mt-4 bg-red-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-red-800 mb-2">Anomaly Reasons</h3>
              <ul className="text-sm text-red-700 space-y-1">
                {result.anomaly_reasons.map((r: string, i: number) => <li key={i}>• {r}</li>)}
              </ul>
            </div>
          )}

          {/* Risk factors */}
          {result.risk_factors?.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Risk Factors</h3>
              <div className="space-y-2">
                {result.risk_factors.map((f: any, i: number) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-sm font-medium">{f.factor}</p>
                    <p className="text-xs text-gray-500">{f.support}</p>
                    <p className="text-xs text-primary-600 mt-1">Contribution: {f.contribution_points} points</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended actions */}
          {result.recommended_actions?.length > 0 && (
            <div className="mt-4 bg-blue-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-800 mb-2">Recommended Actions</h3>
              <ul className="text-sm text-blue-700 space-y-1">
                {result.recommended_actions.map((a: string, i: number) => <li key={i}>→ {a}</li>)}
              </ul>
            </div>
          )}

          {/* Duplicate pairs */}
          {result.duplicate_pairs?.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Potential Duplicates</h3>
              {result.duplicate_pairs.map((d: any, i: number) => (
                <div key={i} className="bg-yellow-50 rounded-lg p-3 mb-2">
                  <p className="text-sm">Similar to: <strong>{d.mp_name}</strong> (Member #{d.member_id})</p>
                  <p className="text-xs text-gray-500">Similarity: {(d.overall_similarity * 100).toFixed(1)}% — {d.reason}</p>
                </div>
              ))}
            </div>
          )}

          {/* LOFO attribution */}
          {result.lofo_attribution && Object.keys(result.lofo_attribution).length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Feature Attribution (LOFO)</h3>
              <ReactECharts option={{
                xAxis: { type: 'category', data: Object.keys(result.lofo_attribution), axisLabel: { rotate: 45, fontSize: 9 } },
                yAxis: { type: 'value', name: 'Value' },
                series: [{ type: 'bar', data: Object.values(result.lofo_attribution), itemStyle: { color: '#3b82f6' } }],
                grid: { left: 50, bottom: 80 },
              }} style={{ height: 200 }} />
            </div>
          )}
        </div>
      )}

      {result?.error && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          Error: {result.error}
        </div>
      )}
    </div>
  );
}
