import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatCompiler from './pages/ChatCompiler';
import Dashboard from './pages/Dashboard';
import BankBrowser from './pages/BankBrowser';
import SessionHistory from './pages/SessionHistory';
import SessionDetail from './pages/SessionDetail';
import RecallSession from './pages/RecallSession';
import SourceUpload from './pages/SourceUpload';
import BankReview from './pages/BankReview';
import ConceptCompiler from './pages/ConceptCompiler';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<ChatCompiler />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/bank" element={<BankBrowser />} />
          <Route path="/sessions" element={<SessionHistory />} />
          <Route path="/sessions/:sessionId" element={<SessionDetail />} />
          <Route path="/recall" element={<RecallSession />} />
          <Route path="/sources" element={<SourceUpload />} />
          <Route path="/review/:conceptId" element={<BankReview />} />
          <Route path="/concepts" element={<ConceptCompiler />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
