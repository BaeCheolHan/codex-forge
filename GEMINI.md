# Codex Rules v2.5.0 (Gemini CLI)

> Gemini CLI용 진입점. Rules는 `.codex/` 폴더와 공유합니다.
>
> **v2.5.0 변경**: 버전 정합성 통일

## Rules

아래 규칙들이 자동으로 로드됩니다:

@./.codex/rules/00-core.md

## Quick Reference

| 명령어 | 동작 |
|--------|------|
| `/memory show` | 로드된 컨텍스트 전체 확인 |
| `/memory refresh` | 컨텍스트 파일 새로고침 |
| `/mcp` | MCP 서버 상태 확인 |
| `/help` | 도움말 |

## Local Search 사용법

### MCP 도구 (권장)
Gemini CLI가 자동으로 local-search MCP 도구를 로드합니다.
`/mcp` 명령으로 상태 확인.

사용 가능한 도구:
- **search**: 키워드/정규식으로 파일/코드 검색 (토큰 절감 핵심!)
- **status**: 인덱스 상태 확인
- **repo_candidates**: 관련 repo 후보 찾기

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
├── .codex-root          # 마커
├── .codex/              # 룰셋/도구 (공유)
│   ├── rules/           # 정책 (Gemini CLI도 사용)
│   ├── scenarios/       # 시나리오 가이드
│   ├── skills/          # 스킬
│   └── tools/           # local-search 등
├── .gemini/             # Gemini CLI 설정
│   └── settings.json
├── GEMINI.md            # 이 파일
├── docs/                # 공유 문서
└── [repos...]           # 실제 저장소들
```

## Codex CLI 사용자

Codex CLI를 사용하시면 `.codex/AGENTS.md`를 참조하세요.

## Navigation

- 상세 규칙: `.codex/rules/00-core.md`
- 온보딩: `.codex/quick-start.md`
- 변경 이력: `docs/_meta/CHANGELOG.md`
