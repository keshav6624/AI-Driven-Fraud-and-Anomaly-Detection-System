import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { api } from '../api/client';

const riskColors: Record<string, string> = {
  LOW: '#22c55e', MEDIUM: '#f59e0b', HIGH: '#ef4444', CRITICAL: '#7c3aed',
};

// Approximate state centroids for the map (lat, lng)
const stateCoords: Record<string, [number, number]> = {
  'ANDHRA PRADESH': [15.9129, 79.7400], 'ARUNACHAL PRADESH': [28.2180, 97.5010],
  'ASSAM': [26.2006, 92.9376], 'BIHAR': [25.0961, 85.3131],
  'CHHATTISGARH': [21.2787, 81.8661], 'GOA': [15.2993, 74.1240],
  'GUJARAT': [22.2587, 71.1924], 'HARYANA': [29.0588, 76.0856],
  'HIMACHAL PRADESH': [31.1048, 77.1734], 'JHARKHAND': [23.6102, 85.2799],
  'KARNATAKA': [15.3173, 75.7139], 'KERALA': [10.8505, 76.2711],
  'MADHYA PRADESH': [22.9734, 78.6569], 'MAHARASHTRA': [19.7515, 75.7139],
  'MANIPUR': [24.6637, 93.9063], 'MEGHALAYA': [25.4670, 91.3662],
  'MIZORAM': [23.1646, 92.9376], 'NAGALAND': [26.1584, 94.5624],
  'ODISHA': [20.9517, 85.0985], 'PUNJAB': [31.1471, 75.3412],
  'RAJASTHAN': [27.0238, 74.2179], 'SIKKIM': [27.5330, 88.5122],
  'TAMIL NADU': [11.1271, 78.6569], 'TELANGANA': [18.1124, 79.0193],
  'TRIPURA': [23.9408, 91.9882], 'UTTAR PRADESH': [26.8467, 80.9462],
  'UTTARAKHAND': [30.0668, 79.0193], 'WEST BENGAL': [22.9868, 87.8550],
  'DELHI': [28.7041, 77.1025], 'JAMMU AND KASHMIR': [33.7782, 76.5762],
  'LADAKH': [34.1526, 77.5771], 'PUDUCHERRY': [11.9416, 79.8083],
  'CHANDIGARH': [30.7333, 76.7794], 'DADRA AND NAGAR HAVELI AND DAMAN AND DIU': [20.3974, 72.8730],
  'LAKSHADWEEP': [10.5667, 72.6417], 'ANDAMAN AND NICOBAR ISLANDS': [11.7401, 92.6586],
};

export default function MapView() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const [points, setPoints] = useState<any[]>([]);
  const [stateFilter, setStateFilter] = useState('');
  const [states, setStates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.getStates().then(setStates); }, []);

  useEffect(() => {
    setLoading(true);
    api.getMapPoints(stateFilter || undefined)
      .then(setPoints)
      .finally(() => setLoading(false));
  }, [stateFilter]);

  useEffect(() => {
    if (!mapContainer.current || points.length === 0) return;
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [78.9629, 22.5937],
      zoom: 5,
    });
    map.addControl(new maplibregl.NavigationControl());

    map.on('load', () => {
      const features = points.map(p => {
        const coords = stateCoords[p.state?.toUpperCase()];
        const lat = (coords ? coords[0] : 22.5) + (Math.random() - 0.5) * 1.5;
        const lng = (coords ? coords[1] : 78.9) + (Math.random() - 0.5) * 1.5;
        return {
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: [lng, lat] },
          properties: { ...p },
        };
      });

      map.addSource('points', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features },
      });

      map.addLayer({
        id: 'points',
        type: 'circle',
        source: 'points',
        paint: {
          'circle-radius': 6,
          'circle-color': [
            'match', ['get', 'risk_level'],
            'CRITICAL', '#7c3aed', 'HIGH', '#ef4444', 'MEDIUM', '#f59e0b', 'LOW', '#22c55e', '#94a3b8',
          ],
          'circle-stroke-width': 1,
          'circle-stroke-color': '#fff',
        },
      });

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
      map.on('mouseenter', 'points', (e: any) => {
        map.getCanvas().style.cursor = 'pointer';
        const props = e.features?.[0]?.properties;
        if (props) {
          popup.setHTML(`
            <div class="text-xs p-1">
              <strong>${props.mp_name}</strong><br/>
              ${props.state} — ${props.constituency}<br/>
              Risk: ${props.risk_level || 'N/A'} (${props.risk_score != null ? Number(props.risk_score).toFixed(1) : '—'})<br/>
              ${props.allocated_amount != null ? `₹${(Number(props.allocated_amount) / 1e7).toFixed(2)} Cr` : ''}
            </div>
          `).addTo(map);
        }
      });
      map.on('mouseleave', 'points', () => {
        map.getCanvas().style.cursor = '';
        popup.remove();
      });
    });

    return () => map.remove();
  }, [points]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Map View</h1>
      <div className="flex gap-3 mb-4">
        <select value={stateFilter} onChange={e => setStateFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All States</option>
          {states.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="text-sm text-gray-500 self-center">{points.length} points</span>
      </div>
      <div ref={mapContainer} className="w-full h-[600px] rounded-xl shadow-sm border border-gray-200" />
    </div>
  );
}
