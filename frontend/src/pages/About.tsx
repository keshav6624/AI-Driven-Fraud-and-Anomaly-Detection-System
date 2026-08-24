export default function About() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">About MPLAD-Sentinel</h1>
      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 max-w-3xl space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-2">Project</h2>
          <p className="text-sm text-gray-600">
            MPLAD-Sentinel is an AI/ML-powered anomaly detection platform for the Member of Parliament Local
            Area Development Scheme (MPLADS). It monitors ₹14.7 crore per-member allocations across 543 MPs
            to identify irregularities, potential duplications, and data quality issues.
          </p>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-2">Smart India Hackathon 2026</h2>
          <p className="text-sm text-gray-600">
            Problem Statement: <strong>SIH26102</strong> — AI-Driven Fraud and Anomaly Detection System
            for MPLADS Data Analytics Portal.
          </p>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-2">ML Pipeline</h2>
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li><strong>Feature Engineering:</strong> 9 analytical features from MP allocation data</li>
            <li><strong>Anomaly Detection:</strong> Ensemble of Robust Z-Score, Isolation Forest, LOF</li>
            <li><strong>Peer Benchmarking:</strong> National and state-level median comparisons</li>
            <li><strong>Duplicate Detection:</strong> TF-IDF char n-grams + token Jaccard similarity</li>
            <li><strong>Risk Scoring:</strong> Composite 0-100 score with 4 weighted components</li>
            <li><strong>Explainability:</strong> LOFO attribution + component decomposition</li>
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-2">Technology Stack</h2>
          <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
            <li><strong>Backend:</strong> FastAPI, SQLAlchemy 2.x, PostgreSQL/SQLite</li>
            <li><strong>Frontend:</strong> React, TypeScript, Tailwind CSS, ECharts, MapLibre GL</li>
            <li><strong>ML:</strong> scikit-learn, pandas, numpy</li>
            <li><strong>Auth:</strong> JWT (HS256), PBKDF2-HMAC-SHA256</li>
          </ul>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-2">Data Disclaimer</h2>
          <p className="text-sm text-gray-600">
            This platform monitors anomalies and irregularities for investigation purposes. Terms like
            "anomaly", "risk", and "potential duplication" do not imply fraud. All findings require
            human verification before any action is taken.
          </p>
        </div>
      </div>
    </div>
  );
}
