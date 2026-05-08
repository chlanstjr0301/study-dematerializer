/**
 * Korean learner-facing representation display adapter.
 *
 * Returns Korean titles, content, and pedagogical annotations for
 * supported concepts. Falls back to raw content for unknown concepts/types.
 */

export interface RepresentationDisplay {
  titleKo: string;
  subtitleKo?: string;
  contentKo: string;
  keyTakeawaysKo?: string[];
  commonPitfallKo?: string;
  rawContent: string;
}

// ---------------------------------------------------------------------------
// Compactness — Korean content
// ---------------------------------------------------------------------------

const COMPACTNESS_FORMAL: RepresentationDisplay = {
  titleKo: '정의 표현',
  subtitleKo: '옹골성(Compactness)의 엄밀한 정의',
  contentKo: `옹골성의 정의는 **"모든 열린 덮개가 유한 부분덮개를 가진다"**이다.

$(X, d)$가 거리공간이고 $K \\subseteq X$일 때, $K$가 **옹골(compact)**하다는 것은:

> $K$의 임의의 열린 덮개 $\\{U_\\alpha\\}_{\\alpha \\in A}$에 대해,
> 유한개의 $\\alpha_1, \\alpha_2, \\ldots, \\alpha_n \\in A$가 존재하여
> $$K \\subseteq U_{\\alpha_1} \\cup U_{\\alpha_2} \\cup \\cdots \\cup U_{\\alpha_n}$$

**강조:** "어떤 열린 덮개 하나"가 아니라 **"모든 열린 덮개"**에 대해 성립해야 한다.

**주의:** $\\mathbb{R}^n$에서는 Heine-Borel 정리에 의해 compact $\\iff$ closed and bounded이지만, 일반 거리공간에서의 정의는 open-cover definition이다.`,
  keyTakeawaysKo: [
    '"모든" 열린 덮개에 대해 유한 부분덮개가 존재해야 한다.',
    '열린 덮개 하나만 확인하는 것은 증명이 아니다.',
    'Heine-Borel은 $\\mathbb{R}^n$ 전용이다.',
  ],
  commonPitfallKo: '"closed and bounded이면 compact"를 일반 거리공간에 적용하는 것은 오류이다. 이는 $\\mathbb{R}^n$에서만 성립한다.',
  rawContent: '',
};

const COMPACTNESS_INTUITIVE: RepresentationDisplay = {
  titleKo: '직관 표현',
  subtitleKo: '옹골성의 직관적 이해',
  contentKo: `아무리 많은 열린집합으로 덮어도, 실제로는 **유한 개만 골라도 충분**하다는 뜻이다.

핵심 직관:
- "무한한 덮개를 **유한한 정보로 압축**할 수 있는 성질"
- 열린집합들이 아무리 많이 필요해 보여도, 유한 개의 "대표 조각"으로 전체를 덮을 수 있다.

**주의:** compact set 자체가 "유한(finite)"이라는 뜻은 **아니다.** $[0,1]$은 비가산 무한이지만 compact이다.

비유: 무한히 많은 뉴스 기사를 **요약본 몇 개**로 전체 내용을 파악할 수 있는 것과 비슷하다.`,
  keyTakeawaysKo: [
    '무한한 덮개 → 유한한 부분덮개로 축약 가능',
    'Compact ≠ finite (무한집합도 compact할 수 있다)',
    '"유한한 정보로 압축 가능"이 핵심 직관',
  ],
  rawContent: '',
};

const COMPACTNESS_VISUAL: RepresentationDisplay = {
  titleKo: '시각 표현',
  subtitleKo: '$[0,1]$과 $(0,1)$의 대비',
  contentKo: `**Compact한 예시: $[0,1]$**
- 끝점 $0$과 $1$이 포함되어 있다.
- $\\mathbb{R}$에서 닫히고(closed) 유계(bounded)이므로 Heine-Borel에 의해 compact.
- 어떤 열린 덮개를 잡아도 유한 부분덮개를 뽑을 수 있다.

**Compact하지 않은 예시: $(0,1)$**
- 끝점 $0$과 $1$ 근처가 빠져 있다.
- 수열 $x_n = 1/n$은 $0$에 수렴하지만, $0 \\notin (0,1)$.
- 덮개 $\\{(1/n, 1)\\}_{n=2,3,\\ldots}$는 유한 부분덮개로 $(0,1)$ 전체를 덮을 수 없다.

**시각적 차이:** $[0,1]$은 "양쪽 끝이 막혀 있어" 빠져나갈 곳이 없다. $(0,1)$은 끝이 열려 있어 점들이 "무한히 탈출"할 수 있다.`,
  keyTakeawaysKo: [
    '$[0,1]$: compact (closed + bounded in $\\mathbb{R}$)',
    '$(0,1)$: not compact (끝점 빠짐 → 유한 부분덮개 불가)',
    '끝점 포함 여부가 compactness에 결정적',
  ],
  rawContent: '',
};

const COMPACTNESS_COUNTEREXAMPLE: RepresentationDisplay = {
  titleKo: '반례 표현',
  subtitleKo: 'Compact하지 않은 집합의 구체적 예시',
  contentKo: `**반례 1: $(0,1)$ — bounded이지만 compact하지 않음**
- 열린 덮개: $\\{(1/n,\\, 1)\\}_{n=2,3,\\ldots}$
- 임의의 유한 부분집합 $\\{(1/n_1, 1), \\ldots, (1/n_k, 1)\\}$을 택하면, $N = \\max(n_1, \\ldots, n_k)$으로 놓으면 $(0, 1/N) \\cap (0,1)$의 점들이 빠진다.
- 따라서 유한 부분덮개가 존재하지 않는다.

**반례 2: $[0, \\infty)$ — closed이지만 compact하지 않음**
- bounded가 아니므로 compact할 수 없다.
- 덮개: $\\{(-1, n)\\}_{n=1,2,\\ldots}$ → 유한 부분덮개 불가

**일반 거리공간에서의 주의:**
- Closed and bounded가 **반드시** compact를 함의하지 않는다.
- 예: 무한차원 Banach 공간의 closed unit ball은 compact하지 않다.`,
  keyTakeawaysKo: [
    'Bounded ⊬ compact ($(0,1)$ 반례)',
    'Closed ⊬ compact ($[0,\\infty)$ 반례)',
    '일반 거리공간에서 closed + bounded ⊬ compact',
  ],
  commonPitfallKo: '"closed and bounded이면 compact"는 $\\mathbb{R}^n$에서만 성립한다. 이를 일반 거리공간으로 확장하면 오류.',
  rawContent: '',
};

const COMPACTNESS_PROOF_SCHEMA: RepresentationDisplay = {
  titleKo: '증명 구조 표현',
  subtitleKo: '옹골성을 증명하는 전략',
  contentKo: `**방법 1: 정의로 직접 증명 (일반 거리공간)**
1. 임의의 열린 덮개 $\\{U_\\alpha\\}_{\\alpha \\in A}$를 잡는다.
2. 유한 개의 $U_{\\alpha_1}, \\ldots, U_{\\alpha_n}$을 추출한다.
3. $K \\subseteq U_{\\alpha_1} \\cup \\cdots \\cup U_{\\alpha_n}$임을 보인다.

**방법 2: Heine-Borel 적용 ($\\mathbb{R}^n$)**
1. $K$가 closed임을 보인다.
2. $K$가 bounded임을 보인다.
3. Heine-Borel 정리를 인용하여 compact를 결론짓는다.

**방법 3: 점열 옹골성 (Sequential Compactness)**
- 거리공간에서 compact $\\iff$ sequentially compact (동치가 증명된 경우)
1. 임의의 수열을 잡는다.
2. 수렴하는 부분수열을 찾는다.
3. 극한값이 $K$ 안에 있음을 보인다.

**흔한 실수:**
- 열린 덮개를 **하나만** 확인하고 compact라고 결론 짓는 것 — **모든** 열린 덮개에 대해 보여야 한다.`,
  keyTakeawaysKo: [
    '정의 증명: "임의의 열린 덮개"에서 시작',
    '$\\mathbb{R}^n$: closed + bounded → Heine-Borel',
    '점열 옹골성: 모든 수열에 수렴 부분수열 존재',
  ],
  commonPitfallKo: '열린 덮개를 하나만 확인하는 것은 옹골성 증명이 아니다. "모든" 열린 덮개에 대해 유한 부분덮개 존재를 보여야 한다.',
  rawContent: '',
};

const COMPACTNESS_DISPLAYS: Record<string, RepresentationDisplay> = {
  formal: COMPACTNESS_FORMAL,
  intuitive: COMPACTNESS_INTUITIVE,
  visual: COMPACTNESS_VISUAL,
  counterexample: COMPACTNESS_COUNTEREXAMPLE,
  proof_schema: COMPACTNESS_PROOF_SCHEMA,
};

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

const DISPLAY_REGISTRY: Record<string, Record<string, RepresentationDisplay>> = {
  compactness: COMPACTNESS_DISPLAYS,
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Get Korean learner-facing display for a representation.
 *
 * If no adapter exists for the concept/type, returns null (caller should fall
 * back to rendering rawContent directly).
 */
export function getRepresentationDisplay(
  conceptId: string,
  representationType: string,
  rawContent: string,
): RepresentationDisplay | null {
  const conceptDisplays = DISPLAY_REGISTRY[conceptId];
  if (!conceptDisplays) return null;

  const display = conceptDisplays[representationType];
  if (!display) return null;

  // Return a copy with rawContent populated
  return { ...display, rawContent };
}
