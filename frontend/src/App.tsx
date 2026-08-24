import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import RiskDashboard from './pages/RiskDashboard';
import Anomalies from './pages/Anomalies';
import Duplicates from './pages/Duplicates';
import MapView from './pages/MapView';
import Investigations from './pages/Investigations';
import Assistant from './pages/Assistant';
import Scoring from './pages/Scoring';
import Admin from './pages/Admin';
import About from './pages/About';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:id" element={<ProjectDetail />} />
            <Route path="risk" element={<RiskDashboard />} />
            <Route path="anomalies" element={<Anomalies />} />
            <Route path="duplicates" element={<Duplicates />} />
            <Route path="map" element={<MapView />} />
            <Route path="investigations" element={<Investigations />} />
            <Route path="assistant" element={<Assistant />} />
            <Route path="scoring" element={<Scoring />} />
            <Route path="admin" element={<Admin />} />
            <Route path="about" element={<About />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
