#!/bin/bash
# Codex Rules v2.5.0 - 언인스톨 스크립트
# 사용법: ./uninstall.sh [workspace_root] [--force]

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

FORCE=false
WORKSPACE_ROOT=""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --force|-f) FORCE=true ;;
        *) 
            if [[ -z "$WORKSPACE_ROOT" && ! "$arg" == --* ]]; then
                WORKSPACE_ROOT="$arg"
            fi
            ;;
    esac
done

# Auto-detect workspace root if not provided
if [[ -z "$WORKSPACE_ROOT" ]]; then
    if [[ -f ".codex-root" ]]; then
        WORKSPACE_ROOT="$(pwd)"
    elif [[ -d "$HOME/Documents/repositories" && -f "$HOME/Documents/repositories/.codex-root" ]]; then
        WORKSPACE_ROOT="$HOME/Documents/repositories"
    elif [[ -d "$HOME/documents/repositories" && -f "$HOME/documents/repositories/.codex-root" ]]; then
        WORKSPACE_ROOT="$HOME/documents/repositories"
    else
        echo_error "Workspace root를 찾을 수 없습니다."
        echo "사용법: ./uninstall.sh [workspace_root]"
        exit 1
    fi
fi

# Resolve to absolute path
WORKSPACE_ROOT="$(cd "$WORKSPACE_ROOT" 2>/dev/null && pwd)"

echo_info "Codex Rules 언인스톨"
echo_info "Workspace: $WORKSPACE_ROOT"
echo ""

# Check if codex-rules is installed
if [[ ! -f "$WORKSPACE_ROOT/.codex-root" ]]; then
    echo_error "Codex Rules가 설치되어 있지 않습니다. (.codex-root 없음)"
    exit 1
fi

# List what will be removed
echo "다음 항목이 삭제됩니다:"
echo ""

ITEMS_TO_REMOVE=()
ITEMS_DESC=()

if [[ -f "$WORKSPACE_ROOT/.codex-root" ]]; then
    ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/.codex-root")
    ITEMS_DESC+=("  - .codex-root (마커 파일)")
fi

if [[ -d "$WORKSPACE_ROOT/.codex" ]]; then
    ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/.codex")
    ITEMS_DESC+=("  - .codex/ (룰셋, 도구, 설정)")
fi

# Root level documentation files
if [[ -f "$WORKSPACE_ROOT/AGENTS.md" ]]; then
    ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/AGENTS.md")
    ITEMS_DESC+=("  - AGENTS.md (진입점)")
fi
if [[ -f "$WORKSPACE_ROOT/GEMINI.md" ]]; then
    ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/GEMINI.md")
    ITEMS_DESC+=("  - GEMINI.md (진입점)")
fi

if [[ -d "$WORKSPACE_ROOT/docs" && -d "$WORKSPACE_ROOT/docs/_meta" ]]; then
    if [[ "$FORCE" != true ]]; then
        read -rp "문서(docs/) 폴더도 삭제하시겠습니까? (yes/no) [no]: " remove_docs
        if [[ "$remove_docs" == "yes" || "$remove_docs" == "y" ]]; then
            ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/docs")
            ITEMS_DESC+=("  - docs/ (공유 문서)")
        else
            echo "  [KEEP] docs/ 폴더는 보존됩니다."
        fi
    else
        # Force mode: default to keep unless --all is specified (future) or just keep safe
        # For now, let's correspond to conservative approach: keep docs in force mode?
        # Actually, standard uninstall usually removes everything. 
        # But to be safe, let's exclude docs from force remove unless explicitly added.
        # Let's add it but maybe we need a flag? 
        # For simplicity in this script: Force remove includes docs to ensure clean state.
        ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/docs")
        ITEMS_DESC+=("  - docs/ (공유 문서)")
    fi
fi

if [[ -f "$WORKSPACE_ROOT/gitignore.sample" ]]; then
    ITEMS_TO_REMOVE+=("$WORKSPACE_ROOT/gitignore.sample")
    ITEMS_DESC+=("  - gitignore.sample")
fi

# Check for index database (new + legacy)
CACHE_DIR_NEW="$HOME/.cache/local-search"
CACHE_DIR_OLD="$HOME/.cache/codex-local-search"
if [[ -d "$CACHE_DIR_NEW" ]]; then
    ITEMS_TO_REMOVE+=("$CACHE_DIR_NEW")
    ITEMS_DESC+=("  - ~/.cache/local-search/ (인덱스 DB)")
fi
if [[ -d "$CACHE_DIR_OLD" ]]; then
    ITEMS_TO_REMOVE+=("$CACHE_DIR_OLD")
    ITEMS_DESC+=("  - ~/.cache/codex-local-search/ (레거시 인덱스 DB)")
fi

for desc in "${ITEMS_DESC[@]}"; do
    echo "$desc"
done

echo ""

# Confirmation
if [[ "$FORCE" != true ]]; then
    echo_warn "이 작업은 되돌릴 수 없습니다!"
    read -rp "정말 삭제하시겠습니까? (yes/no): " confirm
    if [[ "$confirm" != "yes" && "$confirm" != "y" ]]; then
        echo_info "언인스톨 취소됨"
        exit 0
    fi
fi

# Remove items
echo ""
echo_info "삭제 중..."

# Clean up any lingering python cache files in the workspace
find "$WORKSPACE_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$WORKSPACE_ROOT" -name "*.pyc" -delete 2>/dev/null || true

for item in "${ITEMS_TO_REMOVE[@]}"; do
    if [[ -e "$item" ]]; then
        rm -rf "$item"
        echo_info "  삭제됨: $item"
    fi
done

# Check for shell config
echo ""
echo_info "=========================================="
echo_info "언인스톨 완료!"
echo_info "=========================================="
echo ""

# Check for shell config and attempt cleanup
echo_info "셸 설정 파일 확인 중..."
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

if [[ -f "$SHELL_RC" ]] && grep -q "Codex Rules" "$SHELL_RC" 2>/dev/null; then
    echo_info "셸 설정 파일($SHELL_RC)에서 Codex Rules 설정 제거 중..."
    # v2.4.x 마커와 함께 CODEX_HOME 라인 제거
    sed -i '/# Codex Rules v2.4.[0-9] - 자동 생성됨/d' "$SHELL_RC"
    sed -i '/export CODEX_HOME=/d' "$SHELL_RC"
    echo_info "  $SHELL_RC 에서 설정을 제거했습니다."
else
    # Check if CODEX_HOME is set if auto-cleanup didn't run or find it
    if [[ -n "${CODEX_HOME:-}" ]]; then
        echo "추가 정리가 필요할 수 있습니다:"
        echo ""
        echo "1. 셸 설정 파일에서 CODEX_HOME 제거:"
        echo "   ~/.zshrc 또는 ~/.bash_profile에서 다음 라인 삭제:"
        echo "   export CODEX_HOME=\"...\""
        echo ""
        echo "2. 변경 적용:"
        echo "   source ~/.zshrc  # 또는 source ~/.bash_profile"
        echo ""
        echo_warn "현재 CODEX_HOME이 설정되어 있습니다: $CODEX_HOME"
        echo_warn "셸 설정 파일에서 이미 제거되었는지 확인 후 새 터미널을 열거나 source 명령을 실행하세요."
    fi
fi

