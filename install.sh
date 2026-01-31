#!/bin/bash
# Codex Rules v2.5.0 - 원커맨드 설치 스크립트 (Multi-CLI 버전)
# 사용법: ./install.sh [workspace_root] [--codex|--gemini|--all] [--backup|--skip|--quit]
# - workspace_root 미지정 시: 현재 디렉토리를 workspace로 사용하고 git에서 소스를 내려받음
# - git 소스: CODEX_RULES_REPO_URL/CODEX_RULES_REF 환경변수로 오버라이드 가능
#
# CLI 선택 옵션:
#   --codex   Codex CLI만 설치
#   --gemini  Gemini CLI만 설치
#   --all     모두 설치 (기본값)
#   --update  local-search 도구만 git에서 최신 버전으로 업데이트 (설정 유지)
#
# 주요 변경 (v2.5.0):
#   - Multi-CLI 지원: Codex CLI + Gemini CLI
#   - CLI 선택 옵션 추가: --codex, --gemini, --all
#   - GEMINI.md, .gemini/settings.json 생성 지원

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL_DEFAULT="https://github.com/BaeCheolHan/codex-forge.git"
REPO_URL="${CODEX_RULES_REPO_URL:-$REPO_URL_DEFAULT}"
REPO_REF="${CODEX_RULES_REF:-}"
SOURCE_DIR="$SCRIPT_DIR"
SOURCE_MODE="local"
MODE=""
CLI_MODE=""  # codex, gemini, all
BACKUP_DIR=""
HAD_RULES="no"
SOURCE_SNAPSHOT_DIR=""
TEMP_DIR=""

cleanup() {
    if [[ -n "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
    if [[ -n "$SOURCE_SNAPSHOT_DIR" ]]; then
        rm -rf "$SOURCE_SNAPSHOT_DIR"
    fi
}
trap cleanup EXIT

# Parse arguments
WORKSPACE_ROOT=""
for arg in "$@"; do
    case "$arg" in
        --backup) MODE="backup" ;;
        --update) MODE="update" ;;
        --skip) MODE="skip" ;;
        --quit) MODE="quit" ;;
        --codex) CLI_MODE="codex" ;;
        --gemini) CLI_MODE="gemini" ;;
        --all) CLI_MODE="all" ;;
        *) 
            if [[ -z "$WORKSPACE_ROOT" && ! "$arg" == --* ]]; then
                WORKSPACE_ROOT="$arg"
            fi
            ;;
    esac
done

# If workspace root not provided: use current dir
if [[ -z "$WORKSPACE_ROOT" ]]; then
    WORKSPACE_ROOT="$(pwd)"
fi

# Prefer git source when local package structure is missing (install.sh only)
# --update 모드일 때는 항상 git에서 최신 버전을 받음
if [[ "$MODE" == "update" ]]; then
    SOURCE_MODE="git"
    echo_info "업데이트 모드: git에서 최신 버전 다운로드"
elif [[ ! -d "$SCRIPT_DIR/.codex" || ! -d "$SCRIPT_DIR/docs" ]]; then
    SOURCE_MODE="git"
fi

# Resolve to absolute path
WORKSPACE_ROOT="$(cd "$WORKSPACE_ROOT" 2>/dev/null && pwd || echo "$WORKSPACE_ROOT")"

echo_info "Codex Rules v2.5.0 설치 시작 (Multi-CLI 버전)"
echo_info "Workspace: $WORKSPACE_ROOT"
if [[ "$SOURCE_MODE" == "git" ]]; then
    echo_info "Source: git (${REPO_URL}${REPO_REF:+@$REPO_REF})"
else
    echo_info "Source: local ($SCRIPT_DIR)"
fi
echo ""

# CLI 선택 프롬프트 (미지정 시)
if [[ -z "$CLI_MODE" ]]; then
    if [[ ! -t 0 ]]; then
        CLI_MODE="all"
        echo_warn "비대화 환경 감지: 기본값(--all) 사용"
    else
        echo ""
        echo "지원할 CLI를 선택하세요:"
        echo "  1) Codex CLI만"
        echo "  2) Gemini CLI만"
        echo "  3) 모두 (권장)"
        echo ""
        read -rp "선택 (1/2/3) [3]: " cli_choice
        case "$cli_choice" in
            1|codex) CLI_MODE="codex" ;;
            2|gemini) CLI_MODE="gemini" ;;
            *) CLI_MODE="all" ;;
        esac
    fi
fi

echo_info "CLI 모드: $CLI_MODE"
echo ""

# Create workspace if not exists
if [[ ! -d "$WORKSPACE_ROOT" ]]; then
    echo_info "Workspace 디렉토리 생성: $WORKSPACE_ROOT"
    mkdir -p "$WORKSPACE_ROOT"
fi

cd "$WORKSPACE_ROOT"
if [[ -d ".codex/rules" ]]; then
    HAD_RULES="yes"
fi

# If installing from the same repo, snapshot source before any backups/moves.
if [[ "$SOURCE_MODE" == "local" && "$SOURCE_DIR" == "$WORKSPACE_ROOT" ]]; then
    SOURCE_SNAPSHOT_DIR="$(mktemp -d)"
    for dir in ".codex" "docs" ".gemini"; do
        if [[ -d "$SOURCE_DIR/$dir" ]]; then
            cp -r "$SOURCE_DIR/$dir" "$SOURCE_SNAPSHOT_DIR/"
        fi
    done
    for file in ".codex-root" "gitignore.sample" "GEMINI.md"; do
        if [[ -f "$SOURCE_DIR/$file" ]]; then
            cp "$SOURCE_DIR/$file" "$SOURCE_SNAPSHOT_DIR/"
        fi
    done
    SOURCE_DIR="$SOURCE_SNAPSHOT_DIR"
    echo_info "Source: local snapshot ($SOURCE_DIR)"
fi

# Fetch source if needed
if [[ "$SOURCE_MODE" == "git" ]]; then
    if ! command -v git &>/dev/null; then
        echo_error "git을 찾을 수 없습니다. 설치 경로를 인자로 전달하거나 git을 설치하세요."
        exit 1
    fi
    TEMP_DIR="$(mktemp -d)"
    if [[ -n "$REPO_REF" ]]; then
        git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$TEMP_DIR"
    else
        git clone --depth 1 "$REPO_URL" "$TEMP_DIR"
    fi
    SOURCE_DIR="$TEMP_DIR"
fi

if [[ ! -d "$SOURCE_DIR/.codex" || ! -d "$SOURCE_DIR/docs" ]]; then
    echo_error "설치 소스에 .codex 또는 docs가 없습니다: $SOURCE_DIR"
    exit 1
fi

# Check for existing installations
EXISTING_DIRS=()
for dir in ".codex" "docs" ".gemini"; do
    if [[ -d "$dir" ]]; then
        EXISTING_DIRS+=("$dir")
    fi
done
for file in "GEMINI.md" "AGENTS.md"; do
    if [[ -f "$file" ]]; then
        EXISTING_DIRS+=("$file")
    fi
done

if [[ ${#EXISTING_DIRS[@]} -gt 0 ]]; then
    if [[ "$MODE" == "update" ]]; then
        echo_info "기존 설치 발견 (업데이트 모드 진행)"
        echo_info "  - local-search 도구만 최신 버전으로 교체됩니다."
        echo_info "  - docs/, rules/, CLI 설정은 보존됩니다."
    else
        echo_warn "기존 설치 발견: ${EXISTING_DIRS[*]}"
    fi
    
    if [[ -z "$MODE" ]]; then
        echo ""
        echo "선택하세요:"
        echo "  1) backup - 기존 파일 백업 후 덮어쓰기"
        echo "  2) update - local-search 도구만 git에서 업데이트"
        echo "  3) skip   - 기존 디렉토리 유지"
        echo "  4) quit   - 설치 중단"
        echo ""
        read -rp "선택 (1/2/3/4): " choice
        case "$choice" in
            1|backup) MODE="backup" ;;
            2|update) MODE="update" ;;
            3|skip) MODE="skip" ;;
            *) MODE="quit" ;;
        esac
    fi
    
    case "$MODE" in
        backup)
            BACKUP_DIR=".codex-backup-$(date +%Y%m%d%H%M%S)"
            echo_info "백업 생성: $BACKUP_DIR"
            mkdir -p "$BACKUP_DIR"
            for item in "${EXISTING_DIRS[@]}"; do
                if [[ -e "$item" ]]; then
                    mv "$item" "$BACKUP_DIR/"
                fi
            done
            ;;
        skip)
            echo_info "기존 디렉토리 유지 (디렉토리 단위 스킵, 병합 아님)"
            echo_warn "주의: 개별 파일 병합이 아닌 디렉토리 전체 스킵입니다."
            ;;
        quit)
            echo_info "설치 중단"
            echo ""
            echo "수동 설치 방법:"
            echo "  1. 기존 디렉토리 백업 또는 삭제"
            echo "  2. 새 버전 압축 해제: unzip codex-rules-v2.5.0.zip -d /tmp"
            echo "  3. 파일 복사: cp -r /tmp/codex-rules-v2.5.0/* $WORKSPACE_ROOT/"
            exit 0
            ;;
    esac
fi

# =============================================================================
# 공유 파일 설치 (Rules, Tools, Docs)
# =============================================================================
install_shared() {
    echo_step "공유 파일 설치 중..."
    
    # Decide whether to overwrite rules
    RULES_OVERWRITE="yes"
    if [[ "$MODE" == "update" ]]; then
        RULES_OVERWRITE="yes"
    elif [[ "$HAD_RULES" == "yes" ]]; then
        echo ""
        read -rp "기존 rules를 덮어쓸까요? (yes/no): " rules_choice
        case "$rules_choice" in
            y|Y|yes|YES) RULES_OVERWRITE="yes" ;;
            *) RULES_OVERWRITE="no" ;;
        esac
    fi

    # Copy docs
    if [[ -d "$SOURCE_DIR/docs" ]]; then
        if [[ "$MODE" == "update" ]]; then
            echo_info "  docs/ 건너뜀 (업데이트 모드)"
        elif [[ "$MODE" == "skip" && -d "docs" ]]; then
            echo_info "  docs/ 건너뜀 (이미 존재)"
        else
            cp -r "$SOURCE_DIR/docs" .
            echo_info "  docs/ 복사 완료"
        fi
    fi

    # Copy .codex (shared)
    if [[ -d "$SOURCE_DIR/.codex" ]]; then
        if [[ "$MODE" == "skip" && -d ".codex" ]]; then
            echo_info "  .codex/ 건너뜀 (이미 존재)"
        else
            mkdir -p ".codex"
            # 공통 파일 (CLI 무관) - AGENTS.md는 원본 룰
            for item in quick-start.md AGENTS.md; do
                if [[ -f "$SOURCE_DIR/.codex/$item" ]]; then
                    cp "$SOURCE_DIR/.codex/$item" ".codex/$item"
                fi
            done
            # update 모드: local-search만 업데이트
            if [[ "$MODE" == "update" ]]; then
                if [[ -d "$SOURCE_DIR/.codex/tools/local-search" ]]; then
                    # local-search만 교체 (config는 보존)
                    if [[ -d ".codex/tools/local-search" ]]; then
                        # config 백업
                        if [[ -d ".codex/tools/local-search/config" ]]; then
                            cp -r ".codex/tools/local-search/config" "/tmp/local-search-config-backup"
                        fi
                        rm -rf ".codex/tools/local-search"
                    fi
                    cp -r "$SOURCE_DIR/.codex/tools/local-search" ".codex/tools/"
                    # config 복원
                    if [[ -d "/tmp/local-search-config-backup" ]]; then
                        rm -rf ".codex/tools/local-search/config"
                        mv "/tmp/local-search-config-backup" ".codex/tools/local-search/config"
                    fi
                    echo_info "  .codex/tools/local-search 업데이트 완료 (config 보존)"
                fi
            else
                # 일반 설치 모드: 모든 도구 복사
                for dir in tools scenarios skills; do
                    if [[ -d "$SOURCE_DIR/.codex/$dir" ]]; then
                        if [[ -d ".codex/$dir" ]]; then
                            rm -rf ".codex/$dir"
                        fi
                        cp -r "$SOURCE_DIR/.codex/$dir" ".codex/"
                    fi
                done
            fi
            
            # rules 처리 (update 모드에서는 건너뜀)
            if [[ "$MODE" != "update" && "$RULES_OVERWRITE" == "yes" ]]; then
                if [[ -d ".codex/rules" ]]; then
                    rm -rf ".codex/rules"
                fi
                if [[ -d "$SOURCE_DIR/.codex/rules" ]]; then
                    cp -r "$SOURCE_DIR/.codex/rules" ".codex/"
                fi
            elif [[ "$MODE" == "update" ]]; then
                echo_info "  .codex/rules 건너뜀 (업데이트 모드)"
            else
                echo_info "  .codex/rules 건너뜀 (사용자 선택)"
                if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR/.codex/rules" ]]; then
                    cp -r "$BACKUP_DIR/.codex/rules" ".codex/"
                    echo_info "  .codex/rules 복원 (백업에서 유지)"
                fi
            fi
            echo_info "  .codex/ 공유 파일 복사 완료"
        fi
    fi

    # Copy root files
    for file in ".codex-root" "gitignore.sample"; do
        if [[ -f "$SOURCE_DIR/$file" ]]; then
            if [[ "$MODE" == "skip" && -f "$file" ]]; then
                continue
            fi
            cp "$SOURCE_DIR/$file" .
        fi
    done

    # Create .codex-root if not exists
    if [[ ! -f ".codex-root" ]]; then
        touch .codex-root
        echo_info ".codex-root 생성"
    fi

    echo_info "공유 파일 설치 완료"
}

# =============================================================================
# Codex CLI 전용 파일 설치
# =============================================================================
install_codex_cli() {
    echo_step "Codex CLI 파일 설치 중..."
    
    mkdir -p ".codex"
    
    # Root AGENTS.md는 .codex/AGENTS.md를 가리키는 포인터 파일로 생성
    # (Codex CLI는 root에서 AGENTS.md를 읽으므로)
    if [[ ("$MODE" == "skip" || "$MODE" == "update") && -f "AGENTS.md" ]]; then
        echo_info "  AGENTS.md 건너뜀 (이미 존재)"
    else
        cat > "AGENTS.md" << 'AGENTS_EOF'
# Codex Rules

> 이 파일은 Codex CLI 진입점입니다.

## 지침

아래 파일의 모든 지침을 읽고 따르세요:

1. **핵심 규칙**: `./.codex/AGENTS.md` - 전체 가이드라인
2. **상세 정책**: `./.codex/rules/00-core.md` - 정책 정본

위 파일들의 내용을 숙지하고 작업을 진행하세요.
AGENTS_EOF
        echo_info "  AGENTS.md 생성 완료 (포인터 → .codex/AGENTS.md)"
    fi

    # config.toml 설정
    MCP_BLOCK=$(cat << 'MCP_EOF'

[mcp_servers.local-search]
command = "python3"
args = [".codex/tools/local-search/mcp/server.py"]
startup_timeout_sec = 15
tool_timeout_sec = 30

[mcp_servers.local-search.env]
# Workspace root auto-detection (v2.5.0):
# 1. CODEX_WORKSPACE_ROOT env var (if set)
# 2. Search for .codex-root from cwd upward
# 3. Fallback to cwd
MCP_EOF
)

    if [[ ! -f ".codex/config.toml" ]]; then
        cat > ".codex/config.toml" << 'CFG_EOF'
# Workspace-scoped Codex configuration (v2.5.0)
CFG_EOF
        echo "$MCP_BLOCK" >> ".codex/config.toml"
        echo_info "  config.toml 생성 + MCP 설정 추가"
    else
        if ! grep -q "mcp_servers.local-search" ".codex/config.toml" 2>/dev/null; then
            echo "$MCP_BLOCK" >> ".codex/config.toml"
            echo_info "  MCP 서버 설정 추가 (사용자 설정 유지)"
        else
            echo_info "  MCP 서버 설정 이미 존재 (변경 없음)"
        fi
    fi

    echo_info "Codex CLI 파일 설치 완료"
}

# =============================================================================
# Gemini CLI 전용 파일 설치
# =============================================================================
install_gemini_cli() {
    echo_step "Gemini CLI 파일 설치 중..."
    
    # Root GEMINI.md 생성
    if [[ ("$MODE" == "skip" || "$MODE" == "update") && -f "GEMINI.md" ]]; then
        echo_info "  GEMINI.md 건너뜀 (이미 존재)"
    else
        cat > "GEMINI.md" << 'GEMINI_EOF'
# Codex Rules (Gemini CLI)

> 이 파일은 Gemini CLI 진입점입니다.

## Rules

아래 규칙들이 자동으로 로드됩니다:

@./.codex/rules/00-core.md

## Local Search 사용법

### MCP 도구 (권장)
Gemini CLI가 자동으로 local-search MCP 도구를 로드합니다.
`/mcp` 명령으로 상태 확인.

사용 가능한 도구:
- **search**: 키워드/정규식으로 파일/코드 검색
- **status**: 인덱스 상태 확인
- **repo_candidates**: 관련 repo 후보 찾기

## Scenarios

| 시나리오 | 경로 |
|----------|------|
| S0 Simple Fix | .codex/scenarios/s0-simple-fix.md |
| S1 Feature | .codex/scenarios/s1-feature.md |
| S2 Cross-repo | .codex/scenarios/s2-cross-repo.md |
| Hotfix | .codex/scenarios/hotfix.md |

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
GEMINI_EOF
        echo_info "  GEMINI.md 생성 완료"
    fi

    # .gemini/settings.json
    mkdir -p ".gemini"
    if [[ -f "$SOURCE_DIR/.gemini/settings.json" ]]; then
        if [[ ("$MODE" == "skip" || "$MODE" == "update") && -f ".gemini/settings.json" ]]; then
            echo_info "  .gemini/settings.json 건너뜀 (이미 존재)"
        else
            cp "$SOURCE_DIR/.gemini/settings.json" ".gemini/"
            echo_info "  .gemini/settings.json 복사 완료"
        fi
    else
        # 소스에 없으면 생성
        if [[ ! -f ".gemini/settings.json" ]]; then
            cat > ".gemini/settings.json" << 'SETTINGS_EOF'
{
  "$schema": "https://raw.githubusercontent.com/google-gemini/gemini-cli/main/packages/core/src/settings/settings-schema.json",
  "context": {
    "fileName": ["GEMINI.md"]
  },
  "models": {
    "gemini-1.5-flash": { "preview": true },
    "gemini-1.5-pro": { "preview": true },
    "gemini-2.0-flash-exp": { "preview": true }
  },
  "mcpServers": {
    "local-search": {
      "command": "python3",
      "args": [".codex/tools/local-search/mcp/server.py"],
      "timeout": 30000,
      "trust": true
    }
  }
}
SETTINGS_EOF
            echo_info "  .gemini/settings.json 생성 완료"
        fi
    fi

    echo_info "Gemini CLI 파일 설치 완료"
}

# =============================================================================
# 메인 설치 로직
# =============================================================================
echo_info "파일 복사 중..."

# 1. 공유 파일 먼저 설치
install_shared

# 2. CLI 모드에 따라 설치
case "$CLI_MODE" in
    codex)
        install_codex_cli
        ;;
    gemini)
        install_gemini_cli
        ;;
    all)
        install_codex_cli
        install_gemini_cli
        ;;
esac

echo_info "파일 복사 완료"

# Check Python version
echo_info "Python 버전 확인..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    echo_info "  Python $PYTHON_VERSION 발견"
else
    echo_error "Python3를 찾을 수 없습니다. Python 3.8+ 설치가 필요합니다."
    exit 1
fi

# Set up shell configuration for CODEX_HOME (only for codex/all)
if [[ "$CLI_MODE" == "codex" || "$CLI_MODE" == "all" ]]; then
    echo_info "셸 설정 파일 업데이트 중..."

    # Detect shell config file
    if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_RC="$HOME/.zshrc"
    elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$SHELL" == *"bash"* ]]; then
        if [[ -f "$HOME/.bashrc" ]]; then
            SHELL_RC="$HOME/.bashrc"
        elif [[ -f "$HOME/.bash_profile" ]]; then
            SHELL_RC="$HOME/.bash_profile"
        else
            SHELL_RC="$HOME/.bashrc"
        fi
    else
        SHELL_RC="$HOME/.profile"
    fi

    # Check for existing CODEX_HOME
    if grep -q "CODEX_HOME" "$SHELL_RC" 2>/dev/null; then
        EXISTING_CODEX_HOME=$(grep "CODEX_HOME=" "$SHELL_RC" | tail -1 | cut -d= -f2 | tr -d '"' | tr -d "'")
        if [[ "$EXISTING_CODEX_HOME" != "$WORKSPACE_ROOT/.codex" ]]; then
            echo_warn "기존 CODEX_HOME 발견: $EXISTING_CODEX_HOME"
            echo_warn "새 workspace와 충돌할 수 있습니다. 수동 확인 권장."
        fi
    else
        echo "" >> "$SHELL_RC"
        echo "# Codex Rules v2.5.0 - 자동 생성됨" >> "$SHELL_RC"
        echo "export CODEX_HOME=\"$WORKSPACE_ROOT/.codex\"" >> "$SHELL_RC"
        echo_info "  CODEX_HOME 환경변수 추가"
    fi
fi

# Test MCP server
echo_info "MCP 서버 테스트 중..."
cd "$WORKSPACE_ROOT"

MCP_TEST_OUTPUT=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
    python3 .codex/tools/local-search/mcp/server.py 2>/dev/null || echo "FAILED")

if echo "$MCP_TEST_OUTPUT" | grep -q '"protocolVersion"'; then
    echo_info "  MCP 서버 정상 응답 확인"
else
    echo_warn "  MCP 서버 테스트 실패 - 설치 후 수동 확인 필요"
fi

# Done
echo ""
echo_info "=========================================="
echo_info "설치 완료! (v2.5.0 Multi-CLI 버전)"
echo_info "=========================================="
echo ""
echo "설치된 CLI: $CLI_MODE"
echo ""

case "$CLI_MODE" in
    codex)
        echo "다음 단계 (Codex CLI):"
        echo "  1. 셸 설정 적용: source $SHELL_RC"
        echo "  2. workspace로 이동: cd $WORKSPACE_ROOT"
        echo "  3. codex 실행: codex \"안녕\""
        echo "  4. MCP 도구 확인: /mcp"
        ;;
    gemini)
        echo "다음 단계 (Gemini CLI):"
        echo "  1. workspace로 이동: cd $WORKSPACE_ROOT"
        echo "  2. gemini 실행: gemini"
        echo "  3. 컨텍스트 확인: /memory show"
        echo "  4. MCP 도구 확인: /mcp"
        ;;
    all)
        echo "다음 단계:"
        echo ""
        echo "  [Codex CLI]"
        echo "    1. 셸 설정 적용: source $SHELL_RC"
        echo "    2. codex 실행: codex \"안녕\""
        echo "    3. MCP 도구 확인: /mcp"
        echo ""
        echo "  [Gemini CLI]"
        echo "    1. gemini 실행: gemini"
        echo "    2. 컨텍스트 확인: /memory show"
        echo "    3. MCP 도구 확인: /mcp"
        ;;
esac

echo ""
echo "문제 해결:"
echo "  - MCP 연결 실패 시 (HTTP 폴백): python3 .codex/tools/local-search/app/main.py &"
echo "  - HTTP 서버 상태 확인: python3 .codex/tools/local-search/scripts/query.py status"
echo "  - 버전 확인: head -1 $WORKSPACE_ROOT/.codex/AGENTS.md"
echo ""
