import { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { api } from '../api/client';

function Stat({ label, value, color = 'text-gray-900' }: { label: string; value: any; color?: string }) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getOverview().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading dashboard...</div>;
  if (!data) return <div className="text-center py-20 text-red-500">Failed to load data</div>;

  const riskPie = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: [
        { value: data.risk_distribution?.LOW || 0, name: 'Low', itemStyle: { color: '#22c55e' } },
        { value: data.risk_distribution?.MEDIUM || 0, name: 'Medium', itemStyle: { color: '#f59e0b' } },
        { value: data.risk_distribution?.HIGH || 0, name: 'High', itemStyle: { color: '#ef4444' } },
        { value: data.risk_distribution?.CRITICAL || 0, name: 'Critical', itemStyle: { color: '#7c3aed' } },
      ],
    }],
  };

  const stateBar = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.top_risk_states?.map((s: any) => s.state) || [], axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: 'Anomaly Count' },
    series: [{ type: 'bar', data: data.top_risk_states?.map((s: any) => s.anomaly_count) || [], itemStyle: { color: '#3b82f6' } }],
    grid: { left: 50, bottom: 80 },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
        <Stat label="Total Members" value={data.total_members} />
        <Stat label="Total Allocated" value={`₹${(data.total_allocated / 1e7).toFixed(1)}Cr`} />
        <Stat label="Mean Allocation" value={`₹${(data.mean_allocated / 1e7).toFixed(2)}Cr`} />
        <Stat label="Anomalies" value={data.anomaly_count} color="text-red-600" />
        <Stat label="Anomaly Rate" value={`${data.anomaly_rate}%`} color="text-red-600" />
        <Stat label="Benchmark" value={`₹${(data.benchmark_amount / 1e7).toFixed(1)}Cr`} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Risk Distribution</h3>
          <ReactECharts option={riskPie} style={{ height: 300 }} />
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Top States by Anomaly Count</h3>
          <ReactECharts option={stateBar} style={{ height: 300 }} />
        </div>
      </div>
    </div>
  );
}
