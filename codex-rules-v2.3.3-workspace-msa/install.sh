#!/bin/bash
# Codex Rules v2.3.3 - 원커맨드 설치 스크립트 (MCP 버전)
# 사용법: ./install.sh [workspace_root] [--backup|--skip|--quit]
# - workspace_root 미지정 시: 현재 디렉토리를 workspace로 사용하고 git에서 소스를 내려받음
# - git 소스: CODEX_RULES_REPO_URL/CODEX_RULES_REF 환경변수로 오버라이드 가능
#
# 주요 변경 (v2.3.3):
#   - 경로 구조 변경: codex/ → .codex/, tools/ → .codex/tools/
#   - 모든 경로 참조 업데이트
#
# v2.2.1 변경:
#   - config.toml 보존 로직 수정 (사용자 설정 유실 방지)
#   - 문서 zip 구조 안내 수정
#   - 폴백 경로 정리

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL_DEFAULT="https://github.com/BaeCheolHan/codex-forge.git"
REPO_URL="${CODEX_RULES_REPO_URL:-$REPO_URL_DEFAULT}"
REPO_REF="${CODEX_RULES_REF:-}"
SOURCE_DIR="$SCRIPT_DIR"
SOURCE_MODE="local"
MODE=""
BACKUP_DIR=""
HAD_RULES="no"

# Parse arguments
WORKSPACE_ROOT=""
for arg in "$@"; do
    case "$arg" in
        --backup) MODE="backup" ;;
        --skip) MODE="skip" ;;
        --quit) MODE="quit" ;;
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
if [[ ! -d "$SCRIPT_DIR/.codex" || ! -d "$SCRIPT_DIR/docs" ]]; then
    SOURCE_MODE="git"
fi

# Resolve to absolute path
WORKSPACE_ROOT="$(cd "$WORKSPACE_ROOT" 2>/dev/null && pwd || echo "$WORKSPACE_ROOT")"

echo_info "Codex Rules v2.3.3 설치 시작 (MCP 버전)"
echo_info "Workspace: $WORKSPACE_ROOT"
if [[ "$SOURCE_MODE" == "git" ]]; then
    echo_info "Source: git (${REPO_URL}${REPO_REF:+@$REPO_REF})"
else
    echo_info "Source: local ($SCRIPT_DIR)"
fi
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

# Fetch source if needed
TEMP_DIR=""
if [[ "$SOURCE_MODE" == "git" ]]; then
    if ! command -v git &>/dev/null; then
        echo_error "git을 찾을 수 없습니다. 설치 경로를 인자로 전달하거나 git을 설치하세요."
        exit 1
    fi
    TEMP_DIR="$(mktemp -d)"
    cleanup() {
        rm -rf "$TEMP_DIR"
    }
    trap cleanup EXIT
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

# Check for existing installations (v2.3.3: codex/, tools/ 제거됨)
EXISTING_DIRS=()
for dir in ".codex" "docs"; do
    if [[ -d "$dir" ]]; then
        EXISTING_DIRS+=("$dir")
    fi
done

if [[ ${#EXISTING_DIRS[@]} -gt 0 ]]; then
    echo_warn "기존 설치 발견: ${EXISTING_DIRS[*]}"
    
    if [[ -z "$MODE" ]]; then
        echo ""
        echo "선택하세요:"
        echo "  1) backup - 기존 파일 백업 후 덮어쓰기"
        echo "  2) skip   - 기존 디렉토리 유지"
        echo "  3) quit   - 설치 중단"
        echo ""
        read -rp "선택 (1/2/3): " choice
        case "$choice" in
            1|backup) MODE="backup" ;;
            2|skip) MODE="skip" ;;
            *) MODE="quit" ;;
        esac
    fi
    
    case "$MODE" in
        backup)
            BACKUP_DIR=".codex-backup-$(date +%Y%m%d%H%M%S)"
            echo_info "백업 생성: $BACKUP_DIR"
            mkdir -p "$BACKUP_DIR"
            for dir in "${EXISTING_DIRS[@]}"; do
                mv "$dir" "$BACKUP_DIR/"
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
            echo "  2. 새 버전 압축 해제: unzip codex-rules-v2.3.3-workspace-msa.zip -d /tmp"
            echo "  3. 파일 복사: cp -r /tmp/codex-rules-v2.3.3-workspace-msa/* $WORKSPACE_ROOT/"
            echo "  4. 숨김 파일 복사: cp -r /tmp/codex-rules-v2.3.3-workspace-msa/.codex $WORKSPACE_ROOT/"
            exit 0
            ;;
    esac
fi

# Copy files
echo_info "파일 복사 중..."

copy_if_not_exists() {
    local src="$1"
    local dst="$2"
    if [[ "$MODE" == "skip" && -e "$dst" ]]; then
        return
    fi
    mkdir -p "$(dirname "$dst")"
    cp -r "$src" "$dst"
}

# Decide whether to overwrite rules
RULES_OVERWRITE="yes"
if [[ "$HAD_RULES" == "yes" ]]; then
    echo ""
    read -rp "기존 rules를 덮어쓸까요? (yes/no): " rules_choice
    case "$rules_choice" in
        y|Y|yes|YES) RULES_OVERWRITE="yes" ;;
        *) RULES_OVERWRITE="no" ;;
    esac
fi

# Copy docs (can be skipped as a whole)
if [[ -d "$SOURCE_DIR/docs" ]]; then
    if [[ "$MODE" == "skip" && -d "docs" ]]; then
        echo_info "  docs/ 건너뜀 (이미 존재)"
    else
        cp -r "$SOURCE_DIR/docs" .
        echo_info "  docs/ 복사 완료"
    fi
fi

# Copy .codex selectively (rules may be skipped; config is preserved)
if [[ -d "$SOURCE_DIR/.codex" ]]; then
    if [[ "$MODE" == "skip" && -d ".codex" ]]; then
        echo_info "  .codex/ 건너뜀 (이미 존재)"
    else
        mkdir -p ".codex"
        for item in AGENTS.md quick-start.md system-prompt.txt; do
            if [[ -f "$SOURCE_DIR/.codex/$item" ]]; then
                cp "$SOURCE_DIR/.codex/$item" ".codex/$item"
            fi
        done
        for dir in tools scenarios skills; do
            if [[ -d "$SOURCE_DIR/.codex/$dir" ]]; then
                cp -r "$SOURCE_DIR/.codex/$dir" ".codex/"
            fi
        done
        if [[ "$RULES_OVERWRITE" == "yes" ]]; then
            if [[ -d "$SOURCE_DIR/.codex/rules" ]]; then
                cp -r "$SOURCE_DIR/.codex/rules" ".codex/"
            fi
        else
            echo_info "  .codex/rules 건너뜀 (사용자 선택)"
            if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR/.codex/rules" ]]; then
                cp -r "$BACKUP_DIR/.codex/rules" ".codex/"
                echo_info "  .codex/rules 복원 (백업에서 유지)"
            fi
        fi
        # config.toml은 덮어쓰지 않음 (아래에서 병합 처리)
        if [[ ! -f ".codex/config.toml" && -f "$SOURCE_DIR/.codex/config.toml" ]]; then
            cp "$SOURCE_DIR/.codex/config.toml" ".codex/config.toml"
        fi
        echo_info "  .codex/ 복사 완료"
    fi
fi

# Copy root files (v2.3.3: 대부분 .codex/ 또는 docs/_meta/로 이동됨)
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

echo_info "루트 파일 복사 완료"

# Ensure config.toml exists and has MCP server settings (do not overwrite)
MCP_BLOCK=$(cat << 'MCP_EOF'

[mcp_servers.local-search]
command = "python3"
args = [".codex/tools/local-search/mcp/server.py"]
startup_timeout_sec = 15
tool_timeout_sec = 30

[mcp_servers.local-search.env]
# Workspace root auto-detection (v2.3.3):
# 1. CODEX_WORKSPACE_ROOT env var (if set)
# 2. Search for .codex-root from cwd upward
# 3. Fallback to cwd
# Override: CODEX_WORKSPACE_ROOT = "/path/to/workspace"
MCP_EOF
)

if [[ ! -f ".codex/config.toml" ]]; then
    cat > ".codex/config.toml" << 'CFG_EOF'
# Workspace-scoped Codex configuration (v2.3.3)
CFG_EOF
    echo "$MCP_BLOCK" >> ".codex/config.toml"
    echo_info "config.toml 생성 + MCP 설정 추가"
else
    if ! grep -q "mcp_servers.local-search" ".codex/config.toml" 2>/dev/null; then
        echo "$MCP_BLOCK" >> ".codex/config.toml"
        echo_info "MCP 서버 설정 추가 (사용자 설정 유지)"
    else
        echo_info "MCP 서버 설정 이미 존재 (변경 없음)"
    fi
fi

# Check Python version
echo_info "Python 버전 확인..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    echo_info "  Python $PYTHON_VERSION 발견"
else
    echo_error "Python3를 찾을 수 없습니다. Python 3.8+ 설치가 필요합니다."
    exit 1
fi

# Set up shell configuration for CODEX_HOME
echo_info "셸 설정 파일 업데이트 중..."

# Detect shell config file (v2.3.3: improved bash detection)
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$SHELL" == *"bash"* ]]; then
    # Prefer .bashrc for interactive shells (Linux/WSL), .bash_profile for macOS
    if [[ -f "$HOME/.bashrc" ]]; then
        SHELL_RC="$HOME/.bashrc"
    elif [[ -f "$HOME/.bash_profile" ]]; then
        SHELL_RC="$HOME/.bash_profile"
    else
        SHELL_RC="$HOME/.bashrc"  # Create .bashrc if neither exists
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
    # Add CODEX_HOME
    echo "" >> "$SHELL_RC"
    echo "# Codex Rules v2.3.3 - 자동 생성됨" >> "$SHELL_RC"
    echo "export CODEX_HOME=\"$WORKSPACE_ROOT/.codex\"" >> "$SHELL_RC"
    echo_info "  CODEX_HOME 환경변수 추가"
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
echo_info "설치 완료! (v2.3.3 MCP 버전)"
echo_info "=========================================="
echo ""
echo "다음 단계:"
echo "  1. 셸 설정 적용: source $SHELL_RC"
echo "  2. workspace로 이동: cd $WORKSPACE_ROOT"
echo "  3. 프로젝트 신뢰 설정 (최초 1회):"
echo "     codex 실행 후 프로젝트 신뢰 확인 프롬프트에서 'yes' 선택"
echo "  4. codex 실행: codex \"안녕\""
echo ""
echo "MCP 도구 확인:"
echo "  - TUI에서 /mcp 명령 실행"
echo "  - local-search 도구가 등록되어 있어야 함"
echo ""
echo "문제 해결:"
echo "  - MCP 연결 실패 시 (HTTP 폴백): python3 .codex/tools/local-search/app/main.py &"
echo "  - HTTP 서버 상태 확인: python3 .codex/tools/local-search/scripts/query.py status"
echo "  - 버전 확인: head -1 $WORKSPACE_ROOT/.codex/AGENTS.md"
echo ""
