# Quick Start (5분 가이드)

> 이 문서는 Codex Rules의 핵심을 5분 안에 파악하기 위한 온보딩 가이드다.
> 상세 규칙은 `.codex/rules/00-core.md`를 참고한다.

---

## 0. 시작 전 확인 (30초)

### 원커맨드 설치 (권장)

```bash
# 압축 해제 후 (로컬 패키지 사용)
cd codex-rules-v2.4.3-workspace-msa
./install.sh ~/Documents/repositories  # 또는 ~/documents/repositories
source ~/.zshrc  # 또는 ~/.bash_profile

# 완료! codex-cli가 local-search MCP 도구를 자동으로 로드합니다.
```

```bash
# 경로 미지정 시: 현재 디렉토리를 workspace로 사용하고 git에서 최신 소스를 내려받음
cd ~/Documents/repositories
./install.sh
```

```bash
# install.sh만 내려받아 실행
curl -fsSL https://raw.githubusercontent.com/BaeCheolHan/codex-forge/main/install.sh | \
  bash -s -- ~/Documents/repositories
```

### 어디서 실행해야 하나?

```
✅ Workspace root에서 실행 (권장)
   = .codex-root 파일이 있는 디렉토리
   = 여러 repo를 1depth 하위에 가진 상위 디렉토리
   예: ~/Documents/repositories/
       ├── .codex-root          ← 마커 파일
       ├── .codex/              ← 룰셋/도구 (숨김)
       ├── docs/                ← 공유 문서
       ├── payment-service/     ← repo 1
       ├── auth-service/        ← repo 2
       └── batch-service/       ← repo 3

❌ 개별 repo 안에서 실행하면 안됨
   예: ~/Documents/repositories/payment-service/
   → 다른 repo를 볼 수 없고, MSA 후보 제시가 동작 안함
```

### MSA 구조 핵심

```
1. codex-cli는 workspace root에서 실행
2. "payment-service 버그 고쳐줘" → 해당 repo만 Active scope
3. "결제 관련 코드 찾아줘" → local-search가 전체 repo 검색 → 후보 제시
4. repo 미지정 요청 → Change 금지, 후보 2~3개 제시 후 선택
```

### 수동 설치 (선택)

```bash
# 1. workspace root 이동
cd ~/Documents/repositories

# 2. 마커 파일 생성 (없으면)
touch .codex-root

# 3. 룰셋 압축 해제 + 복사
unzip /path/to/codex-rules-v2.4.3-workspace-msa.zip -d /tmp
# 주의: zip은 codex-rules-v2.4.3-workspace-msa/ 폴더를 생성함
cp -r /tmp/codex-rules-v2.4.3-workspace-msa/.codex .
cp -r /tmp/codex-rules-v2.4.3-workspace-msa/docs .
cp /tmp/codex-rules-v2.4.3-workspace-msa/.codex-root .
# 결과: .codex/, docs/ 생성됨 (깔끔!)

# 4. 환경변수 설정 (선택, 셸 프로필에 추가)
export CODEX_HOME="$HOME/Documents/repositories/.codex"
```

### 매번 실행 전 확인

```bash
# 1. workspace root로 이동
cd ~/Documents/repositories  # 또는 .codex-root가 있는 곳

# 2. 필수 파일 존재 확인
ls .codex-root .codex/AGENTS.md .codex/rules/00-core.md

# 3. codex-cli 실행
codex "안녕"

# 4. MCP 도구 확인 (TUI에서)
/mcp
# local-search 도구가 보여야 함: search, status, repo_candidates
```

### 실패 시 진단

```bash
# 문제: .codex-root를 찾을 수 없음
→ 해결: touch .codex-root (workspace root에서 실행)

# 문제: AGENTS.md를 찾을 수 없음
→ 해결: 룰셋 zip을 workspace root에 압축 해제

# 문제: MCP local-search 도구 안 보임
→ 해결: .codex/config.toml 확인, 프로젝트 신뢰 설정 확인

# 문제: MCP 서버 오류
→ 폴백: python3 .codex/tools/local-search/app/main.py &
→ 확인: python3 .codex/tools/local-search/scripts/query.py status
```

### 완료 조건 (DoD)

- [ ] `.codex-root` 파일 존재
- [ ] `.codex/rules/00-core.md` 읽기 가능
- [ ] `/mcp` 명령으로 local-search 도구 확인

---

## 1. 핵심 원칙 (30초)

**우선순위**: P0 > P1 > P2 > P3 > P4

| 우선순위 | 내용 |
|----------|------|
| P0 | 안전/보안/데이터 파괴 방지 |
| P1 | 정확성/무결성/버그 최소화 |
| P2 | 범위/통제/비용(토큰/변경량) |
| P3 | 속도/편의 |
| P4 | 문서/지식 |

**핵심**: 안전 > 품질 > 비용 > 편의

---

## 2. 토큰 절감: Local Search 우선

파일 탐색 전 **반드시** local-search 먼저!

| Before (토큰 낭비) | After (토큰 절감) |
|-------------------|------------------|
| Glob 전체 탐색 → 20개 파일 → 12000 토큰 | local-search → 3개 파일 → 900 토큰 |

**MCP 도구 사용**:
- `search`: 키워드로 파일/코드 검색
  - **Tip**: `repo` 스코프를 지정하면 정확도가 올라갑니다.
  - **Tip**: 결과가 0건이면 필터(`type`, `path`)를 제거해보세요.
- `status`: 인덱스 상태 및 설정 확인 (숨김 파일 포함 여부 등)
- `list_files`: 특정 파일이 인덱스에 있는지 확인 (디버깅용)
- `repo_candidates`: 관련 repo 후보

**인덱싱 확인**:
파일이 검색되지 않으면 `list_files path_pattern="filename"`으로 인덱스 포함 여부를 확인하세요.
자세한 내용: `.codex/rules/00-core.md` > "Local Search 우선 원칙"

---

## 3. 스케일과 게이트 (1분)

변경 규모에 따라 요구사항이 달라진다.

| 스케일 | 파일 수 | LOC | 스펙 | 롤백 | 재확인 | 문서 |
|--------|---------|-----|------|------|--------|------|
| S0 | ≤3 | ≤300 | - | - | - | 경로만 |
| S1 | 4-10 | ≤1000 | 필수 | - | - | 필수 |
| S2 | 11-20 | ≤2000 | 필수 | 필수 | - | 필수 |
| S3 | 21-30 | ≤3000 | 필수 | 필수 | 필수 | 필수 |

**하드캡**: 30 files AND 3000 LOC 초과 금지. **파일 수와 LOC 중 높은 스케일 적용.**

---

## 4. 자주 쓰는 토글 (1분)

첫 줄 첫 토큰으로 모드를 전환한다.

| 토글 | 동작 |
|------|------|
| `/plan` | 계획만 (코드 변경/실행 금지) |
| `/code` | 변경 준비 토글 (승인 아님) |
| `/mcp` | MCP 도구 상태 확인 |
| `@path` | 파일 찾기/네비게이션 |
| `스킬 OFF` | 스킬 기능 중지 |

---

## 5. 진행 의도 표현 (1분)

아래 표현이 있으면 "진행" 의도로 간주한다.

**진행 신호**: 진행/적용/반영/구현/수정/고쳐/리팩토링/해결/만들어/추가해/전부/다/전체

**계획만 신호**: 계획만/설계만/리뷰만/코드 변경하지 마

**위험 행동**: 아래는 1회 재확인 필요
- 파괴/비가역: 삭제, DDL, 마이그레이션
- 외부 영향: 배포, 인프라, 네트워크
- 대규모: S2+ (11+ files)

---

## 6. MSA 환경 규칙 (30초)

multi-repo 환경에서는:

1. **repo 미지정이면 Change 금지**
2. 후보 2~3개 제시 → 사용자 선택
3. 선택된 repo만 Active scope로 고정

**후보 제시 순서**:
1. Local Search 결과 (MCP `repo_candidates` 도구)
2. skills-index.md
3. 1depth 목록 + README 확인

---

## 7. 증거 규칙 (30초)

**완료/해결/확인은 증거 없이 선언 금지**

| 작업 | 필요 증거 |
|------|-----------|
| Change | 경로 + diff (1~3 hunk) |
| Run | 명령 + 출력 (≤10줄) |

---

## 8. 시나리오 선택 (30초)

상황에 맞는 시나리오 가이드를 참고한다.

| 상황 | 가이드 |
|------|--------|
| 단순 버그 수정 (≤3 files) | `.codex/scenarios/s0-simple-fix.md` |
| 기능 추가 (4-10 files) | `.codex/scenarios/s1-feature.md` |
| Cross-repo 변경 | `.codex/scenarios/s2-cross-repo.md` |
| 긴급 핫픽스 | `.codex/scenarios/hotfix.md` |

---

## 다음 단계

- 상세 규칙: `.codex/rules/00-core.md`
- 체크리스트: `.codex/rules/01-checklists.md`
- 지식 루프: `.codex/rules/02-knowledge.md`
