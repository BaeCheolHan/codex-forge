# 00 Core (정본)

모든 규칙의 단일 소스. 다른 파일은 이 문서를 참조만 한다.

## 목표
- 자연어 요청 처리, 실행은 **진행 의도/예산/증거/체크리스트**로 통제
- 최우선 **코드 품질/버그 최소화(P1)**, 그 다음 비용(토큰/탐색/변경량)
- 문서 **기본 ON**(S0는 lightweight): 교훈/부채/상태를 초압축으로 누적

## 우선순위 (P0→P4)

| 순위 | 내용 |
|------|------|
| P0 | 안전/보안/데이터 파괴 방지 |
| P1 | 정확성/무결성/버그 최소화 |
| P2 | 문서화/지식 누적 |
| P3 | 속도/편의 |
| P4 | 범위/통제/비용(토큰/변경량) |

## 용어
- **Workspace root**: `.codex-root`가 있는 디렉토리
- **Repo**: workspace 1depth 하위 폴더
- **Active scope**: 이번 작업에서 읽거나/수정하는 repo 집합
- **Code files**: 소스/설정/테스트 등 제품 코드
- **Doc files**: `docs/**`, `.codex/**` (별도 예산)

## 스케일 및 게이트 (S0→S3)

| 스케일 | 파일 수 | LOC | 스펙 | 롤백 | 재확인 | 문서 |
|--------|---------|-----|------|------|--------|------|
| S0 | ≤3 | ≤300 | - | - | - | 경로만 |
| S1 | 4-10 | ≤1000 | Mini Spec | - | - | 필수 |
| S2 | 11-20 | ≤2000 | Mini Spec | 필수 | - | 필수 |
| S3 | 21-30 | ≤3000 | Mini Spec | 필수 | 필수 | 필수 |

**하드캡**: ≤30 code files AND ≤3000 LOC. 초과 금지.

### 스케일 판정 규칙

**1. 파일 수 vs LOC (둘 중 높은 스케일 적용)**
- 파일 ≤3이지만 LOC 2000 → **S2** (LOC 기준)
- 파일 15개지만 LOC 200 → **S2** (파일 수 기준)

**2. 변경 타입별 최소 스케일**

| 변경 타입 | 최소 스케일 | 비고 |
|-----------|-------------|------|
| 비즈니스 코드 | 테이블 기준 | 파일/LOC로 판정 |
| 문서만 (`docs/**`) | 스케일 제외 | 별도 예산 |
| 룰 파일 (`.codex/rules/*`) | S1+ | 전파 영향 큼 |
| 툴 코드 (`.codex/tools/**`) | S2+ | 인프라 영향 |
| 보안/네트워크/인덱스 | S3 | 고위험 |
| 설정 파일 (`.codex/*`) | S1+ | 동작 변경 가능 |

**3. 롤백 정의**
- **S2 롤백**: `git revert` 가능한 단위 커밋 + 검증 방법 1개
- **S3 롤백**: 위 + 설정/데이터 원복 절차 명시 (백업 위치, 복구 명령)

## 예산

| 작업 | 기본 | 확장 |
|------|------|------|
| Read | ≤10 files / ≤1200 lines | ≤30 files / ≤3000 lines |
| Change | ≤3 files / ≤300 LOC | 단계 게이트 적용 |

## MSA 타겟팅 (P0)
- repo/service 미지정이면 **Change/Read Expand 금지**
- 후보 2~3개 제시 → 사용자 선택 → Active scope 고정
- **후보 제시 순서**: (1) local-search `/repo-candidates` (2) 1depth+README

## Local Search 우선 원칙 (P2: 토큰 절감)

**목적**: 불필요한 파일 탐색을 방지하여 토큰 30-50% 절감

### MCP 도구 사용 (v2.3.0+)
local-search가 MCP 도구로 등록되어 있다면 (`/mcp`로 확인):
1. **search**: 키워드로 파일/코드 검색
2. **status**: 인덱스 상태 확인

MCP 미등록 시: `python3 .codex/tools/local-search/scripts/query.py search "keyword"`

### 필수 사용 시나리오

| 상황 | 필수 행동 | 금지 |
|------|-----------|------|
| 파일 위치 모름 | local-search `search` 먼저 | Glob 전체 탐색 |
| 키워드 검색 | local-search > grep | 추측 경로 접근 |
| Cross-repo 탐색 | local-search로 전체 검색 | 수동 탐색 |
| **지식 문서 조회** | local-search로 검색 (lessons/glossary/API/ERD) | 직접 경로 접근 |

### 예시: Before vs After

**Before (토큰 낭비)**:
```
User: "로그인 코드 찾아줘"
AI: Glob **/*auth* → 20개 파일 읽기 → 12000 토큰
```

**After (토큰 절감)**:
```
User: "로그인 코드 찾아줘"
AI: local-search "login auth" → 3개 파일 → 900 토큰 (92% 절감)
```

### 예외 허용
- local-search 결과 0건 → Glob 허용
- local-search 서버 미응답 → grep 허용 (에러 로그 명시)

## 게이트 & 워크플로우

상세 내용: `03-gate.md`

- 진행 의도 게이트 (3단계 승인)
- Phase Prompt (S1+ 개발 흐름)
- 증거 규칙
- Run 정책 (SAFE)
- Design Review 트리거

## 토큰/비용 절감

| 항목 | 상한 |
|------|------|
| 기본 응답 | 8줄 |
| 계획 | 6 bullets |
| diff | 3 hunk |
| 로그/출력 | 10줄 |

- 같은 내용 재설명 금지 (링크/키워드로만 참조)
- 문서 본문은 저장용, 컨텍스트에는 요약/경로만

## Knowledge Capture
- `docs/**` 산출물은 **한국어** (코드 식별자는 영문 유지)
- "분석/설계/API 분석" 요청 시 코드 변경 없어도 **문서 저장 필수**
- **S1+ 완료 시 문서 미작성 = 작업 미완료로 간주**
- 채팅 출력: 요약(≤8줄) + 저장 경로 목록만

## 산출물 경로

| 종류 | 경로 |
|------|------|
| 기획/설계 | `docs/<repo>/plan/plan-<id>.md` |
| API 분석 | `docs/<repo>/api/<api-name>.md` |
| ERD | `docs/<repo>/erd/<api-name>.md` |
| 통합 ERD | `docs/_shared/erd/erd.md` |
| 용어집 | `docs/_shared/glossary/glossary.md` |
| 교훈 | `docs/_shared/lessons-learned/lessons-learned.md` |

## 환각 억제
- 완료/해결/확인은 **재현 가능한 증거** 필수
- 도구 실패/모호 결과 시: (1) 실패 명시 (2) 확보 증거만 사용 (3) 빈칸 상상 금지

## Skills
- 절차 재사용 문서 패키지
- **사용자 승인 없이 생성/설치/사용 금지**
- approval/budget/evidence/checklist 우회 불가

## 레포 청결
- 커밋 허용: `docs/_shared/lessons-learned/**`, `docs/_shared/erd/**`, `docs/_shared/glossary/**`, `docs/<repo>/api/**`, `docs/<repo>/erd/**`
- 비커밋(로컬): `docs/**/state/**`