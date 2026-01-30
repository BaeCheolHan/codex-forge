# Codex Rules v2.5.0

> Codex CLI 진입점. 공유 룰은 `.codex/rules/`에 있습니다.
>
> **v2.5.0 변경**: Multi-CLI 지원 및 버전 정합성 통일

## 핵심 규칙

아래 규칙 파일을 참조하세요:

- `.codex/rules/00-core.md` - 핵심 정책 (정본)

## Quick Start

```
/mcp                    # MCP 도구 상태 확인
search query="keyword"  # local-search로 파일 검색
```

## Local Search 사용법

### MCP 도구 (권장)
codex-cli가 자동으로 local-search MCP 도구를 로드합니다.
`/mcp` 명령으로 상태 확인.

사용 가능한 도구:
- **search**: 키워드/정규식으로 파일/코드 검색
- **status**: 인덱스 상태 확인
- **repo_candidates**: 관련 repo 후보 찾기
- **list_files**: 인덱싱된 파일 목록 조회 (v2.4.2)

### 토큰 절감 원칙
파일 탐색 전 **반드시** local-search로 먼저 검색!
- Before: 전체 탐색 → 12000 토큰
- After: local-search → 900 토큰 (92% 절감)

## Scenarios

| 시나리오 | 경로 |
|----------|------|
| S0 Simple Fix | `.codex/scenarios/s0-simple-fix.md` |
| S1 Feature | `.codex/scenarios/s1-feature.md` |
| S2 Cross-repo | `.codex/scenarios/s2-cross-repo.md` |
| Hotfix | `.codex/scenarios/hotfix.md` |

## 디렉토리 구조

```
workspace/
├── AGENTS.md            # 이 파일 (Codex CLI 진입점)
├── GEMINI.md            # Gemini CLI 진입점
├── .codex-root          # 마커
├── .codex/
│   ├── AGENTS.md        # 원본 (git 저장)
│   ├── config.toml      # MCP 서버 설정
│   ├── rules/           # 정책 (공유)
│   ├── scenarios/       # 시나리오 가이드
│   ├── skills/          # 스킬
│   └── tools/           # local-search 등
├── docs/                # 공유 문서
└── [repos...]           # 실제 저장소들
```

## Navigation

- 상세 규칙: `.codex/rules/00-core.md`
- 온보딩: `.codex/quick-start.md`
- 변경 이력: `docs/_meta/CHANGELOG.md`

## Gemini CLI 사용자

Gemini CLI를 사용하시면 `GEMINI.md`를 참조하세요.
