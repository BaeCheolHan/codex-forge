# Codex Forge v2.6.0

> AI 코딩 에이전트를 위한 규칙 프레임워크

MSA 환경에서 AI CLI(Codex CLI, Gemini CLI)를 효과적으로 사용하기 위한 룰셋입니다.

## 핵심 목표

- **토큰 절감**: local-search로 불필요한 탐색 최소화 (30-50% 절감)
- **버그 감소**: 지식 문서(lessons/API/ERD/glossary) 참조로 재실수 방지
- **코드 품질**: Phase Prompt로 개발 흐름(분석→설계→리뷰→코딩→테스트) 자연스럽게 유도
- **안전한 변경**: 3단계 승인 게이트 + 증거 기반 완료

## 빠른 시작

```bash
# 자동 설치 - CLI 선택 가능 (1. Codex / 2. Gemini / 3. 모두)
./install.sh /path/to/workspace

# 특정 CLI만 설치
./install.sh /path/to/workspace --codex   # Codex CLI만
./install.sh /path/to/workspace --gemini  # Gemini CLI만
./install.sh /path/to/workspace --all     # 모두 (기본값)

# 현재 디렉토리에 설치 (git에서 최신 소스 다운로드)
./install.sh

# install.sh만 내려받아 실행
curl -fsSL https://raw.githubusercontent.com/BaeCheolHan/codex-forge/main/install.sh | \
  bash -s -- /path/to/workspace
```

## 지원 CLI

| CLI | 진입점 | 설정 파일 |
|-----|--------|-----------|
| **Codex CLI** | `AGENTS.md` (root) | `.codex/config.toml` |
| **Gemini CLI** | `GEMINI.md` (root) | `.gemini/settings.json` |

## 주요 기능

- **Local Search 우선**: 파일 탐색 전 local-search MCP 필수 사용
- **지식 누적**: lessons/debt/state 자동 문서화로 재탐색 방지
- **Phase Prompt**: S1+ 작업 시 단계별 흐름 자연스럽게 제안
- **MSA 타겟팅**: 멀티 레포지토리 환경에서 타겟 서비스 명시
- **Multi-CLI**: Codex CLI와 Gemini CLI 모두 지원

## 구조

```
AGENTS.md            # Codex CLI 진입점 (install.sh가 생성)
GEMINI.md            # Gemini CLI 진입점 (install.sh가 생성)
.codex-root          # workspace 마커
.codex/              # 룰셋, 도구, 설정 (공유)
  ├── AGENTS.md      # 원본 (git 저장, root로 복사됨)
  ├── config.toml    # Codex CLI MCP 설정
  ├── rules/         # 핵심 규칙 (공유)
  ├── tools/         # local-search 등 (공유)
  └── quick-start.md # 온보딩 가이드
.gemini/             # Gemini CLI 설정
  └── settings.json  # Gemini CLI MCP 설정
docs/                # 공유 문서 (visible)
install.sh           # 설치 스크립트
uninstall.sh         # 제거 스크립트
```

## 문서

- 온보딩: `.codex/quick-start.md`
- 설치 상세: `docs/_meta/SETUP.md`
- 변경 이력: `docs/_meta/CHANGELOG.md`
- 프로젝트 개요: `docs/_meta/PROJECT_OVERVIEW.md`

## 제거

```bash
./uninstall.sh
```
