# Codex Rules v2.3.3

MSA 환경에서 codex-cli를 효과적으로 사용하기 위한 룰셋입니다.

## 빠른 시작

```bash
# 자동 설치 (권장)
./install.sh /path/to/workspace

# 또는 경로 미지정 시 현재 디렉토리에 설치 (git에서 최신 소스 다운로드)
./install.sh

# install.sh만 내려받아 실행
curl -fsSL https://raw.githubusercontent.com/BaeCheolHan/codex-forge/main/install.sh | \
  bash -s -- /path/to/workspace

# 또는 수동 설치 - .codex/quick-start.md 참고
```

## 주요 기능

- **토큰 절감**: local-search MCP로 파일 탐색 최소화 (30-50% 절감)
- **안전한 게이트**: 3단계 승인 프로세스 (`/code` → 타겟 → 스케일 확인)
- **MSA 지원**: 멀티 레포지토리 환경에서 타겟 서비스 명시
- **지식 누적**: docs/ 자동 문서화

## 구조

```
.codex-root          # workspace 마커
.codex/              # 룰셋, 도구, 설정 (숨김)
  ├── AGENTS.md      # codex-cli 진입점
  ├── config.toml    # MCP 서버 설정
  ├── rules/         # 핵심 규칙
  ├── tools/         # local-search 등
  └── quick-start.md # 온보딩 가이드
docs/                # 공유 문서 (visible)
install.sh           # 설치 스크립트
uninstall.sh         # 제거 스크립트
```

## 문서

- 온보딩: `.codex/quick-start.md`
- 설치 상세: `docs/_meta/SETUP.md`
- 변경 이력: `docs/_meta/CHANGELOG.md`

## 제거

```bash
./uninstall.sh
```
