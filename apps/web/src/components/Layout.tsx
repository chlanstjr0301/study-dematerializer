import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function Layout({ children }: { children: React.ReactNode }) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <>
      <nav className="layout-nav">
        <div className="nav-primary">
          <strong>
            <Link to="/" style={{ color: '#fff', textDecoration: 'none' }}>
              공부해체분석기
            </Link>
          </strong>
          <Link to="/">공부하기</Link>
          <Link to="/recall">인출연습</Link>
          <Link to="/dashboard">대시보드</Link>
        </div>
        <div className="nav-advanced">
          <button
            className="nav-advanced-toggle"
            onClick={() => setShowAdvanced(prev => !prev)}
          >
            {showAdvanced ? '개발자 도구 \u25BE' : '개발자 도구 \u25B8'}
          </button>
          {showAdvanced && (
            <div className="nav-advanced-links">
              <Link to="/sources">소스 관리</Link>
              <Link to="/bank">문제은행</Link>
              <Link to="/concepts">컴파일러</Link>
              <Link to="/sessions">세션</Link>
            </div>
          )}
        </div>
      </nav>
      <main className="layout-content">{children}</main>
    </>
  );
}
