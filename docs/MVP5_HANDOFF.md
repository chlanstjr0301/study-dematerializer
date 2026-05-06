# MVP5 Handoff: Integrated Study Session

## 1. MVP5 완성 내용

MVP5는 Gonghaebun의 핵심 학습 루프를 통합 UI로 구현한다.
학습자가 개념 이름을 입력하면 아래 6단계를 한 화면에서 완주할 수 있다:

1. **진단** — 사전 지식 입력, 취약점 파악
2. **선행 확인** — 선행 개념 자가 체크
3. **표현 학습** — 5가지 표현(정의/직관/시각/반례/증명구조) 순차 학습 + 자기 설명
4. **오개념 체크** — 참/거짓 퀴즈
5. **인출 연습** — 교재 없이 자유 서술 (White Recall)
6. **세션 정리** — 숙련도 업데이트 + STUDY.md 기록

모든 LLM 호출은 `MockLLMClient`로 동작한다 (`LLM_DISABLED=1`).

---

## 2. 실행 방법

### Backend

```bash
cd C:\dev\study-dematerializer
pip install -e .
python -m uvicorn apps.api.main:app --reload --port 8000
```

### Frontend

```bash
cd C:\dev\study-dematerializer\apps\web
npm install   # 최초 1회
npm run dev
```

브라우저에서 http://localhost:5173 접속.

---

## 3. 소스 준비

학습 세션을 생성하려면 소스 파일이 필요하다.

```bash
mkdir -p data/gonghaebun/default/sources
cp tests/data/sample_source.md data/gonghaebun/default/sources/
```

또는 `/sources` 페이지에서 파일을 업로드할 수 있다.

---

## 4. 사용 방법

1. http://localhost:5173 에서 "옹골성", "연결성", "균등연속" 중 하나 입력
2. 분석 결과에서 "공부 시작" 클릭
3. 6단계를 순서대로 진행
4. 세션 완료 시 STUDY.md 자동 업데이트

### 지원 개념 (MVP5)

| concept_id | 한국어명 | 별칭 |
|------------|---------|------|
| compactness | 옹골성 | 컴팩트, compact |
| connectedness | 연결성 | connected |
| uniform_continuity | 균등연속 | 고른연속 |

---

## 5. 수동 검증 체크리스트

> **Status: Manual verification pending**
> 아래 절차는 자동 테스트와 별도로 수동 확인이 필요하다.

| # | 동작 | 예상 결과 |
|---|------|----------|
| 1 | http://localhost:5173 접속 | ChatCompiler 페이지 (한국어) |
| 2 | "옹골성" 입력, 전송 | 분석 카드 + "공부 시작" 링크 |
| 3 | "공부 시작" 클릭 | /study/compactness, 세션 생성 (201) |
| 4 | 진단 작성 후 제출 | 진단 결과 표시, 2단계 자동 이동 |
| 5 | 선행 확인, "다음 단계" | 3단계 이동 |
| 6 | 5개 표현 모두 확인 | 자기 설명 입력란 표시 |
| 7 | formal 자기 설명 제출 | 평가 결과 (정확도 + 피드백) |
| 8 | proof_schema 자기 설명 제출 | 평가 결과 |
| 9 | "다음 단계" | 4단계 이동 |
| 10 | 오개념 T/F 모두 응답 | 정답/오답 피드백 |
| 11 | "다음 단계" | 5단계 이동 |
| 12 | 인출 작성 후 "제출" | 인출 평가 결과 |
| 13 | "다음 단계로" | 6단계 이동 |
| 14 | 세션 자동 완료 | 숙련도 테이블, 다음 복습일 |
| 15 | STUDY.md 확인 | compactness 섹션 존재 |
| 16 | "대시보드로 돌아가기" | Dashboard 정상 로드 |

### 에러 케이스

| # | 동작 | 예상 |
|---|------|------|
| E1 | /study/없는개념 | "지원하지 않는 개념입니다" |
| E2 | 소스 없이 세션 생성 | "소스 파일을 먼저 업로드하세요" |
| E3 | recall 없이 complete | 400 에러 |
| E4 | self-explain 없이 complete | 400 에러 |

---

## 6. 런타임 아티팩트

세션 완료 후 생성되는 파일:

### `data/gonghaebun/default/runs/{session_id}/`

| 파일 | 내용 |
|------|------|
| session.json | 파이프라인 메타데이터 |
| representation_set.json | 5가지 표현 콘텐츠 |
| prerequisite_graph.json | 선행 그래프 |
| diagnosis.json | 오개념 목록 |
| recall_tasks.json | 인출 과제 정의 |
| study_session_state.json | MVP5 세션 상태 (핵심) |
| STUDY.patch.md | 감사 추적 패치 |

### `data/gonghaebun/default/banks/{concept_id}/`

| 파일 | 내용 |
|------|------|
| questions.generated.json | 자동 생성 문제 |
| questions.accepted.json | 수락된 문제 (자동 복사) |

### `data/gonghaebun/default/STUDY.md`

세션 완료 시 `apply_patch()`로 업데이트. `.bak` 백업 생성 후 검증.

---

## 7. API 요약

### Study Session Endpoints

| Method | Path | 설명 |
|--------|------|------|
| POST | /api/study-session | 세션 생성 (8단계 파이프라인 실행) |
| GET | /api/study-session/{id} | 세션 상태 조회 |
| POST | /api/study-session/{id}/diagnose | 진단 제출 (자동 step 2) |
| POST | /api/study-session/{id}/advance | 단계 진행 |
| POST | /api/study-session/{id}/self-explain | 자기 설명 제출 |
| POST | /api/study-session/{id}/recall | 인출 응답 제출 |
| POST | /api/study-session/{id}/complete | 세션 완료 |

### 관련 Endpoints

| Method | Path | 설명 |
|--------|------|------|
| GET | /api/bank/{concept_id} | 문제은행 조회 |
| GET | /api/due | 복습 예정 개념 |
| GET | /api/weak | 취약 표현 목록 |
| POST | /api/compiler/analyze | 개념 분석 (ChatCompiler) |
| POST | /api/sources/upload | 소스 파일 업로드 |

---

## 8. 알려진 한계

| 한계 | 설명 |
|------|------|
| Mock LLM | 모든 평가는 fixture 기반 (실제 LLM 미사용) |
| 페이지 새로고침 | selfExplanationResults, recallResult 미복원 (sessionStorage 한계) |
| 단일 개념 | 한 번에 하나의 개념만 학습 |
| 동시 세션 | 같은 concept에 대한 동시 세션 미지원 |
| 재시도 | WhiteRecallStep에서 제출 후 재작성 불가 (UI 비활성화) |
| 선행 학습 | PrerequisiteStep에서 개별 선행 개념 학습 링크 없음 |
| 채점 정확도 | MockLLMClient는 고정 fixture 반환 (실제 학습 내용과 무관) |

---

## 9. 다음 단계 후보

1. **실제 LLM 활성화** — OpenAI Responses API로 자기 설명/인출 평가
2. **다중 개념 학습 계획** — 선행 그래프 기반 연속 학습
3. **간격 반복 자동화** — next_review_date 기반 알림/대시보드 강화
4. **재시도 UX** — 인출 재시도, 자기 설명 수정 제출
5. **실제 채점 품질 평가** — evals/ golden set 기반 정확도 측정
6. **배포** — Oracle/Railway 배포 + 인증

---

## 10. 테스트 현황

```
python -m pytest tests/ -q   → 1050 passed
npm run build                → clean (0 errors)
```

자동 테스트는 모든 API 경로, 에러 케이스, apply_patch 실패 시나리오를 커버한다.
수동 smoke test는 별도 수행 필요.
