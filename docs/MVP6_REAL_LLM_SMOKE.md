# MVP6 Real LLM Smoke Test 문서

> **상태**: Manual real-LLM execution pending
>
> 이 문서는 real LLM smoke test 절차를 정리한 것이다.
> 실제 OpenAI API를 사용한 검증이 완료되면 결과를 기록한다.

---

## 1. 현재 LLM 경로 요약

### Mock 모드 (기본값)

```
GONGHAEBUN_LLM_DISABLED=1  →  MockLLMClient (절대 override)
```

- `tests/fixtures/{concept_id}/{stage_key}.json` 기반 결정론적 응답
- API 호출 없음, 비용 없음
- 모든 자동 테스트에서 사용

### OpenAI 모드

```
GONGHAEBUN_LLM_DISABLED=0
GONGHAEBUN_LLM_PROVIDER=openai
GONGHAEBUN_LLM_MODEL=gpt-5.5
OPENAI_API_KEY=<your_openai_api_key>
```

- `OpenAIClient` → OpenAI Responses API
- `OPENAI_API_KEY` 필수, 없으면 `LLMAPIKeyError` 발생
- `__fixture__:` marker는 자동 strip (실제 API에 전송되지 않음)

### Factory 흐름

```
get_llm_client()  [src/gonghaebun/llm/factory.py]
  ├─ GONGHAEBUN_LLM_DISABLED=1 → MockLLMClient (무조건)
  └─ GONGHAEBUN_LLM_DISABLED=0
       ├─ GONGHAEBUN_LLM_PROVIDER=mock → MockLLMClient
       └─ GONGHAEBUN_LLM_PROVIDER=openai
            ├─ OPENAI_API_KEY 없음 → LLMAPIKeyError
            └─ OPENAI_API_KEY 있음 → OpenAIClient(model=GONGHAEBUN_LLM_MODEL)
```

---

## 2. Pipeline Stage별 LLM 사용 방식

### Structured Output 사용 Stage (provider-level JSON schema 강제)

| Stage | 함수 | 스키마 | 검증 |
|-------|------|--------|------|
| 자기 설명 평가 (Stage 5) | `complete_structured()` | `EVALUATION_OUTPUT_SCHEMA` | provider + `validate_evaluation_output()` |
| Recall 평가 | `complete_structured()` | `EVALUATION_OUTPUT_SCHEMA` | provider + `validate_evaluation_output()` |
| LLM Grading | `complete_structured()` | `LLM_GRADING_OUTPUT_SCHEMA` | provider + `validate_llm_output()` + retry + fallback |

### Prompt-guided Stage (스키마 강제 없음)

| Stage | 함수 | 호출 횟수 | 비고 |
|-------|------|-----------|------|
| Stage 3 (표현 생성) | `complete()` | 5회 | plain text, JSON fallback 파싱 |
| Stage 4 (오개념 체크) | `complete_json()` | 1회 | JSON 파싱만 |
| Stage 6 (인출 과제 생성) | `complete_json()` | 1회 | JSON 파싱만 |

### 한계

- Stage 3/4/6은 prompt-guided → LLM 출력 품질 미검증 (MVP6-1 범위)
- JSON 파싱 실패 시 `LLMResponseError` 발생 → API 500
- 이 smoke test는 "호출 성공 + 구조 정합성" 확인만 수행

### LLM 호출 합계

세션 1회 ≈ 10 API 호출:
- 세션 생성: 7회 (Stage 3 x5 + Stage 4 x1 + Stage 6 x1)
- Self-explain: 2회 (formal + proof_schema)
- Recall 평가: 1회

---

## 3. Smoke Test 절차

### 3.1. 사전 준비

#### 로컬 환경

```bash
git pull origin main
pip install -e ".[dev,web,llm]"
```

#### .env 설정

```bash
cp .env.example .env
# .env를 편집하여 다음 값 설정:
#   GONGHAEBUN_LLM_DISABLED=0
#   GONGHAEBUN_LLM_PROVIDER=openai
#   GONGHAEBUN_LLM_MODEL=gpt-5.5
#   OPENAI_API_KEY=<your_openai_api_key>
```

> **주의**: `.env` 파일은 `.gitignore`에 포함되어 있다. 절대 커밋하지 마라.

#### Factory 확인

```bash
python -c "
import os
os.environ['GONGHAEBUN_LLM_DISABLED'] = '0'
os.environ['GONGHAEBUN_LLM_PROVIDER'] = 'openai'
# OPENAI_API_KEY가 .env에 설정되어 있어야 함
from dotenv import load_dotenv; load_dotenv()
from gonghaebun.llm.factory import get_llm_client
c = get_llm_client()
print(f'Client: {type(c).__name__}')
print(f'Model: {c._model}')
"
```

예상 출력:
```
Client: OpenAIClient
Model: gpt-5.5
```

#### 소스 파일 준비

```bash
mkdir -p data/gonghaebun/default/sources
cp tests/data/sample_source.md data/gonghaebun/default/sources/
```

### 3.2. 서버 실행

```bash
uvicorn apps.api.main:app --reload --port 8000
```

### 3.3. 기본 확인

```bash
curl http://127.0.0.1:8000/api/health
# → {"status":"ok"}

curl http://127.0.0.1:8000/api/ready
# → {"ready":true,"checks":{"data_dir":"ok","study_md":"ok"or"missing","llm":"enabled"}}
```

### 3.4. 학습 세션 실행

#### 방법 A: 브라우저

1. `http://localhost:5173` 접속
2. "옹골성" 입력 → 학습 시작
3. 진단 → 선행 확인 → 표현 학습 → 오개념 체크 순서대로 진행
4. 자기 설명 2회 (formal, proof_schema)
5. 인출 연습 → STUDY.md 업데이트 → 완료

#### 방법 B: 스크립트

```bash
python scripts/smoke_real_llm.py --allow-real-llm
```

스크립트는 10단계 순차 HTTP 호출을 수행한다:
1. GET /api/health
2. GET /api/ready
3. POST /api/study-session (세션 생성, 7 LLM 호출)
4. POST diagnose
5. POST self-explain (formal, 1 LLM 호출)
6. POST self-explain (proof_schema, 1 LLM 호출)
7. POST advance x3 (prerequisites, representations, misconceptions)
8. POST recall (1 LLM 호출)
9. POST advance (recall)
10. POST complete

> **주의**: `--allow-real-llm` 없이 실행하면 즉시 exit 1로 중단된다.

### 3.5. Artifact 확인

| 파일 | 확인 사항 |
|------|----------|
| `data/gonghaebun/default/runs/{session_id}/study_session_state.json` | `completed: true`, `study_md_updated: true` |
| `data/gonghaebun/default/runs/{session_id}/STUDY.patch.md` | 패치 내용 존재 |
| `data/gonghaebun/default/STUDY.md` | compactness(옹골성) 섹션 존재 |

---

## 4. Oracle 서버 배포 시 검증

```bash
ssh user@oracle-server
cd /path/to/study-dematerializer
git pull origin main
pip install -e ".[dev,web,llm]"

# .env 설정 (위와 동일)

# 포트 열기 (테스트용)
sudo ufw allow 8000/tcp

# 서버 실행
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 &

# Smoke test
python scripts/smoke_real_llm.py --allow-real-llm --base-url http://127.0.0.1:8000

# 테스트 완료 후 정리
kill %1  # uvicorn 종료
sudo ufw deny 8000/tcp  # 포트 닫기
```

---

## 5. 비용 및 보안 가드

### 비용

- 학습 세션 1회 ≈ 10 LLM API 호출 (gpt-5.5)
- `GONGHAEBUN_LLM_MAX_CALLS_PER_SESSION=20` (기본 상한)
- **실험 후 반드시 `GONGHAEBUN_LLM_DISABLED=1`로 복원**

### 보안

| 항목 | 상태 |
|------|------|
| `.env` | `.gitignore`에 포함 (커밋 불가) |
| `data/gonghaebun/` | `.gitignore`에 포함 |
| `runs/` | `.gitignore`에 포함 |
| API key 로그 출력 | smoke script에서 값 출력 금지 |
| prompt/response 로그 | smoke script에서 본문 출력 금지 |
| 외부 접근 | `GONGHAEBUN_API_HOST=127.0.0.1` (기본값은 localhost only) |
| Oracle 배포 | 테스트 후 8000 포트 닫기 필수 |

### 보안 확인 명령

```bash
git check-ignore -v .env                    # .env gitignored 확인
git status --short                          # untracked 확인
grep -R "OPENAI_API_KEY=sk-" . || true      # tracked 파일에 key 없음 확인
```

---

## 6. 실패 대응 표

| # | 실패 증상 | 원인 | 확인 위치 | 해결 |
|---|----------|------|----------|------|
| 1 | `LLMAPIKeyError` | `OPENAI_API_KEY` 미설정 | `factory.py:50-53` | `.env`에 key 설정 |
| 2 | `/api/ready` → `llm: no_api_key` | 환경변수 미로드 | `health.py` | uvicorn 재시작 |
| 3 | 502 (self-explain/recall) | API rate limit / timeout | `study_session.py:107,125` | 재시도 또는 `LLM_TIMEOUT_SECONDS` 증가 |
| 4 | Session creation 500 | Stage 3/4/6 JSON parse 실패 | `study_session.py:47` | prompt-guided 한계 (재시도) |
| 5 | Connection refused | 서버 미실행 | — | uvicorn 확인 |
| 6 | 422: 소스 파일 미발견 | `sources/` 비어있음 | `study_session.py:43-44` | `sample_source.md` 복사 |
| 7 | OpenAI 인증 실패 (401) | 잘못된 API key | `openai_client.py` | key 재발급 |
| 8 | Timeout (30s 초과) | 네트워크/모델 과부하 | `openai_client.py` retry | `GONGHAEBUN_LLM_TIMEOUT_SECONDS` 증가 |
| 9 | STUDY.md update 실패 | 파일 권한/경로 | `study_session.py:140` | `DATA_ROOT` 확인 |

---

## 7. 한계 및 주의사항

- Stage 3 (표현 생성), Stage 4 (오개념 체크), Stage 6 (인출 과제 생성)은
  prompt-guided → LLM 출력 품질 미검증 (MVP6-1 범위)
- 이 smoke test는 "호출 성공 + 구조 정합성" 확인만 수행
- 실제 학습 품질 평가는 evals/ golden set 기반 별도 파이프라인 필요
- `gpt-5.5` 모델 고정 (다른 모델은 이 smoke test에서 지원하지 않음)

---

## 8. 검증 결과

> Manual real-LLM execution pending.
>
> 실제 검증 완료 시 이 섹션에 결과를 기록한다:
> - 날짜
> - session_id
> - 성공/실패
> - runtime (초)
> - 사용 모델
> - 특이 사항
