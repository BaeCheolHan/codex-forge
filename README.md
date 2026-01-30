# Codex Rules v2.4.2

MSA 환경에서 AI CLI(Codex CLI, Gemini CLI)를 효과적으로 사용하기 위한 룰셋입니다.

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

- **토큰 절감**: local-search MCP로 파일 탐색 최소화 (30-50% 절감)
- **안전한 게이트**: 3단계 승인 프로세스 (`/code` → 타겟 → 스케일 확인)
- **MSA 지원**: 멀티 레포지토리 환경에서 타겟 서비스 명시
- **지식 누적**: docs/ 자동 문서화
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
