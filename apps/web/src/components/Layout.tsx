import { Link } from 'react-router-dom';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <nav className="layout-nav">
        <strong>Gonghaebun</strong>
        <Link to="/">Dashboard</Link>
        <Link to="/bank">Bank</Link>
        <Link to="/sessions">Sessions</Link>
        <Link to="/recall">Recall</Link>
      </nav>
      <main className="layout-content">{children}</main>
    </>
  );
}
