import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import BankBrowser from './pages/BankBrowser';
import SessionHistory from './pages/SessionHistory';
import SessionDetail from './pages/SessionDetail';
import RecallSession from './pages/RecallSession';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/bank" element={<BankBrowser />} />
          <Route path="/sessions" element={<SessionHistory />} />
          <Route path="/sessions/:sessionId" element={<SessionDetail />} />
          <Route path="/recall" element={<RecallSession />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
