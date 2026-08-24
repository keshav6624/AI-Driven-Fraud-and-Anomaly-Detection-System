import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

export default function RiskDashboard() {
  const [overview, setOverview] = useState<any>(null);
  const [scatter, setScatter] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getOverview(), api.getAnomalyScatter()])
      .then(([o, s]) => { setOverview(o); setScatter(s); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-400 py-20 text-center">Loading...</p>;

  const riskPie = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '75%'],
      data: [
        { value: overview?.risk_distribution?.LOW || 0, name: 'Low', itemStyle: { color: '#22c55e' } },
        { value: overview?.risk_distribution?.MEDIUM || 0, name: 'Medium', itemStyle: { color: '#f59e0b' } },
        { value: overview?.risk_distribution?.HIGH || 0, name: 'High', itemStyle: { color: '#ef4444' } },
        { value: overview?.risk_distribution?.CRITICAL || 0, name: 'Critical', itemStyle: { color: '#7c3aed' } },
      ],
      label: { formatter: '{b}: {c}' },
    }],
  };

  const scatterData = scatter.filter(s => s.risk_score != null).map(s => ({
    value: [s.allocated_amount ? s.allocated_amount / 1e7 : 0, s.risk_score],
    name: s.mp_name,
    itemStyle: { color: s.risk_level === 'CRITICAL' ? '#7c3aed' : s.risk_level === 'HIGH' ? '#ef4444' : s.risk_level === 'MEDIUM' ? '#f59e0b' : '#22c55e' },
  }));

  const scatterChart = {
    tooltip: { formatter: (p: any) => `${p.name}<br/>Allocated: ₹${p.value[0].toFixed(2)}Cr<br/>Risk: ${p.value[1]}` },
    xAxis: { name: 'Allocated (₹ Cr)', type: 'value' },
    yAxis: { name: 'Risk Score', type: 'value', max: 100 },
    series: [{ type: 'scatter', data: scatterData, symbolSize: 8 }],
    grid: { left: 60, right: 20, bottom: 40 },
  };

  const stateRisk = overview?.top_risk_states?.slice(0, 12) || [];
  const stateChart = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: stateRisk.map((s: any) => s.state), axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value' },
    series: [
      { name: 'Low', type: 'bar', stack: 'risk', data: stateRisk.map((s: any) => s.risk_distribution?.LOW || 0), itemStyle: { color: '#22c55e' } },
      { name: 'Medium', type: 'bar', stack: 'risk', data: stateRisk.map((s: any) => s.risk_distribution?.MEDIUM || 0), itemStyle: { color: '#f59e0b' } },
      { name: 'High', type: 'bar', stack: 'risk', data: stateRisk.map((s: any) => s.risk_distribution?.HIGH || 0), itemStyle: { color: '#ef4444' } },
      { name: 'Critical', type: 'bar', stack: 'risk', data: stateRisk.map((s: any) => s.risk_distribution?.CRITICAL || 0), itemStyle: { color: '#7c3aed' } },
    ],
    grid: { left: 50, bottom: 80 },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Risk Dashboard</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk Distribution</h3>
          <ReactECharts option={riskPie} style={{ height: 300 }} />
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Allocation vs Risk Score</h3>
          <ReactECharts option={scatterChart} style={{ height: 300 }} />
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk by State (Stacked)</h3>
          <ReactECharts option={stateChart} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  );
}
