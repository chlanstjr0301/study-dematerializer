import { Link } from 'react-router-dom';

interface SessionSummaryStepProps {
  conceptId: string;
  canonicalNameKo: string;
  stepsCompleted: string[];
}

const TOTAL_STEPS = 6;

export default function SessionSummaryStep({ conceptId, canonicalNameKo, stepsCompleted }: SessionSummaryStepProps) {
  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>세션 정리</h2>

      <div style={{
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        borderRadius: 8, padding: '16px 20px', marginBottom: 20,
      }}>
        <p style={{ fontWeight: 600, color: '#15803d', marginBottom: 8 }}>
          학습 세션을 완료했습니다!
        </p>
        <p style={{ fontSize: 14, color: '#166534' }}>
          오늘 다룬 내용: <strong>{canonicalNameKo}</strong> ({conceptId})
        </p>
        <p style={{ fontSize: 13, color: '#166534', marginTop: 4 }}>
          완료한 단계: {stepsCompleted.length}/{TOTAL_STEPS}
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        <h3 style={{ marginBottom: 10, fontSize: 15 }}>숙련도 변화</h3>
        <table className="table-simple">
          <thead>
            <tr>
              <th>표현</th>
              <th>이전</th>
              <th>이후</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>정의 (formal)</td>
              <td><span className="badge badge-partial">부분</span></td>
              <td><span className="badge badge-partial">(미정)</span></td>
            </tr>
            <tr>
              <td>직관 (intuitive)</td>
              <td><span className="badge badge-overdue">미확인</span></td>
              <td><span className="badge badge-partial">(미정)</span></td>
            </tr>
          </tbody>
        </table>
        <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 8 }}>
          * 숙련도 업데이트는 다음 버전에서 자동으로 반영됩니다.
        </p>
      </div>

      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, color: '#555' }}>다음 복습일: <strong>(미정)</strong></p>
        <p style={{ fontSize: 14, color: '#555' }}>남은 선행 개념: <strong>(미정)</strong></p>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link className="submit-btn" to="/dashboard" style={{ textDecoration: 'none' }}>
          대시보드로 돌아가기
        </Link>
        <Link className="submit-btn" to="/" style={{ textDecoration: 'none', background: '#64748b' }}>
          다른 개념 공부하기
        </Link>
      </div>
    </div>
  );
}
