# Codex Rules v2.3.3 (workspace-msa)

> 정본 경로: `.codex/rules/00-core.md` | 이 문서는 진입점.
>
> **v2.3.0 변경**: 구조 단순화 - 모든 룰셋/도구가 `.codex/` 아래로 통합

## Rule Map

| 영역 | 경로 | 설명 |
|------|------|------|
| Core Policy | `.codex/rules/00-core.md` | 스케일/예산/MSA/증거 |
| Checklists | `.codex/rules/01-checklists.md` | S1+용 체크리스트 |
| Knowledge | `.codex/rules/02-knowledge.md` | 지식/부채/상태 |
| Hotfix | `.codex/rules/99-hotfix.md` | 핫픽스 정책 |

## Quick Start

```bash
# 1. 필수 파일 확인
ls .codex-root .codex/AGENTS.md .codex/rules/00-core.md

# 2. MCP 도구 확인 (/mcp 명령 사용)
# local-search 도구가 등록되어 있어야 함

# 3. 도움이 필요하면
cat .codex/quick-start.md
```

## Local Search 사용법 (v2.3.3+)

### 방법 1: MCP 도구 (권장)
codex-cli가 자동으로 local-search MCP 도구를 로드합니다.
TUI에서 `/mcp` 명령으로 상태 확인.

사용 가능한 도구:
- **search**: 키워드/정규식으로 파일/코드 검색 (토큰 절감 핵심!)
  - v2.3.3: file_types, path_pattern, exclude_patterns, recency_boost, use_regex 지원
- **status**: 인덱스 상태 확인
- **repo_candidates**: 관련 repo 후보 찾기

### 방법 2: HTTP 서버 폴백
MCP 연결 실패 시 HTTP 서버를 수동 시작:
```bash
# HTTP 서버 시작 (백그라운드)
python3 .codex/tools/local-search/app/main.py &

# 상태 확인
python3 .codex/tools/local-search/scripts/query.py status
```

### 토큰 절감 원칙
파일 탐색 전 **반드시** local-search로 먼저 검색!
- Before: Glob 전체 탐색 → 12000 토큰
- After: local-search → 900 토큰 (92% 절감)

자세한 내용: `.codex/rules/00-core.md` > "Local Search 우선 원칙"

## Scenarios

| 시나리오 | 경로 |
|----------|------|
| S0 Simple Fix | `.codex/scenarios/s0-simple-fix.md` |
| S1 Feature | `.codex/scenarios/s1-feature.md` |
| S2 Cross-repo | `.codex/scenarios/s2-cross-repo.md` |
| Hotfix | `.codex/scenarios/hotfix.md` |

## 네비게이션

- `@path` — 파일/폴더 네비게이션
- `/plan` — 계획 모드 (변경 금지)
- `/code` — 코드 변경 준비

## 디렉토리 구조 (v2.3.0)

```
workspace/
├── .codex-root          # 마커
├── .codex/              # 룰셋/도구 (숨김)
│   ├── AGENTS.md        # 이 파일
│   ├── config.toml      # 설정
│   ├── rules/           # 정책
│   ├── scenarios/       # 시나리오 가이드
│   └── tools/           # local-search 등
├── docs/                # 공유 문서 (보임)
└── [repos...]           # 실제 저장소들
```
