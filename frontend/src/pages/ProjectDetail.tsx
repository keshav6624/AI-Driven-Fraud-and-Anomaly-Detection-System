import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

const riskColor: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800', MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-red-100 text-red-800', CRITICAL: 'bg-purple-100 text-purple-800',
};

export default function ProjectDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) api.getProject(Number(id)).then(setData).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="text-gray-400 py-20 text-center">Loading...</p>;
  if (!data) return <p className="text-red-500 py-20 text-center">Not found</p>;

  const riskGauge = {
    series: [{
      type: 'gauge', min: 0, max: 100,
      detail: { formatter: '{value}', fontSize: 20 },
      data: [{ value: data.risk?.risk_score || 0, name: 'Risk Score' }],
      axisLine: { lineStyle: { width: 12, color: [[0.25, '#22c55e'], [0.45, '#f59e0b'], [0.65, '#ef4444'], [1, '#7c3aed']] } },
    }],
  };

  const anomalyRadar = data.anomaly ? {
    radar: {
      indicator: [
        { name: 'Robust Z', max: 1 }, { name: 'Isolation Forest', max: 1 }, { name: 'LOF', max: 1 },
      ],
    },
    series: [{ type: 'radar', data: [{ value: [
      data.anomaly.score_robust_z, data.anomaly.score_isolation_forest, data.anomaly.score_lof,
    ], name: 'Anomaly Scores' }] }],
  } : null;

  const riskBar = data.risk ? {
    xAxis: { type: 'category', data: ['Financial', 'Data Quality', 'Duplicate', 'Interest'] },
    yAxis: { type: 'value', max: 100 },
    series: [{ type: 'bar', data: [
      data.risk.financial_risk, data.risk.data_quality_risk, data.risk.duplicate_risk, data.risk.interest_risk,
    ], itemStyle: { color: '#3b82f6' } }],
    grid: { left: 50, bottom: 30 },
  } : null;

  return (
    <div>
      <Link to="/projects" className="text-sm text-primary-600 hover:underline">← Back to Projects</Link>
      <div className="mt-4 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold">{data.mp_name}</h1>
            <p className="text-gray-500 mt-1">{data.constituency}, {data.state}</p>
          </div>
          {data.risk && (
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${riskColor[data.risk.risk_level] || ''}`}>
              {data.risk.risk_level} Risk
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">Allocated Amount</p>
            <p className="text-lg font-bold">{data.entitlement?.allocated_amount != null ? `₹${(data.entitlement.allocated_amount / 1e7).toFixed(2)} Cr` : 'Missing'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">Benchmark Ratio</p>
            <p className="text-lg font-bold">{data.features?.benchmark_ratio != null ? `${(data.features.benchmark_ratio * 100).toFixed(1)}%` : '—'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">National Percentile</p>
            <p className="text-lg font-bold">{data.features?.national_percentile != null ? `${(data.features.national_percentile * 100).toFixed(1)}%` : '—'}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">Anomaly Votes</p>
            <p className="text-lg font-bold">{data.anomaly?.anomaly_votes ?? '—'} / 3</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {data.risk && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk Score</h3>
            <ReactECharts option={riskGauge} style={{ height: 250 }} />
          </div>
        )}
        {anomalyRadar && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Anomaly Detection</h3>
            <ReactECharts option={anomalyRadar} style={{ height: 250 }} />
          </div>
        )}
        {riskBar && (
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 lg:col-span-2">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk Components</h3>
            <ReactECharts option={riskBar} style={{ height: 250 }} />
          </div>
        )}
      </div>

      {data.explanation && (data.explanation.risk_factors?.length > 0 || data.explanation.recommended_actions?.length > 0) && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Explanation</h3>
          {data.explanation.risk_factors?.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-1">Risk Factors</p>
              <ul className="list-disc list-inside text-sm text-gray-700">
                {data.explanation.risk_factors.map((f: string, i: number) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}
          {data.explanation.recommended_actions?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 mb-1">Recommended Actions</p>
              <ul className="list-disc list-inside text-sm text-gray-700">
                {data.explanation.recommended_actions.map((a: string, i: number) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
