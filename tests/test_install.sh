#!/bin/bash
# install.sh 테스트 스크립트
# 사용법: bash tests/test_install.sh
# Windows에서: bash -c "cd /mnt/d/repositories/codex-forge && sed 's/\r$//' tests/test_install.sh | bash"

set +e  # 에러에서 종료하지 않음 (테스트 계속 진행)

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# PROJECT_ROOT 감지 (파이프 실행시에도 작동하도록)
if [[ -n "${BASH_SOURCE[0]}" && "${BASH_SOURCE[0]}" != "bash" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    # 파이프로 실행시 현재 디렉토리 사용
    PROJECT_ROOT="$(pwd)"
fi
TEST_BASE="/tmp/codex-forge-tests"
PASS_COUNT=0
FAIL_COUNT=0

echo_pass() { echo -e "${GREEN}[PASS]${NC} $1"; ((++PASS_COUNT)); }
echo_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((++FAIL_COUNT)); }
echo_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

cleanup() {
    rm -rf "$TEST_BASE"
}

setup_test() {
    local test_name="$1"
    TEST_DIR="$TEST_BASE/$test_name"
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR"
    echo_info "테스트: $test_name"
}

run_install() {
    local args="$*"
    cd "$PROJECT_ROOT"
    # Windows CRLF 처리
    sed 's/\r$//' install.sh | bash -s -- "$TEST_DIR" $args 2>&1
}

# =============================================================================
# 테스트 케이스
# =============================================================================

test_basic_all_install() {
    setup_test "basic_all_install"
    
    run_install --all > /dev/null
    
    # 필수 파일 확인
    [[ -f "$TEST_DIR/AGENTS.md" ]] && echo_pass "AGENTS.md 생성됨 (root)" || echo_fail "AGENTS.md 없음"
    [[ -f "$TEST_DIR/.codex/AGENTS.md" ]] && echo_pass ".codex/AGENTS.md 생성됨" || echo_fail ".codex/AGENTS.md 없음"
    [[ -f "$TEST_DIR/GEMINI.md" ]] && echo_pass "GEMINI.md 생성됨" || echo_fail "GEMINI.md 없음"
    [[ -f "$TEST_DIR/.codex-root" ]] && echo_pass ".codex-root 생성됨" || echo_fail ".codex-root 없음"
    [[ -f "$TEST_DIR/.codex/config.toml" ]] && echo_pass ".codex/config.toml 생성됨" || echo_fail ".codex/config.toml 없음"
    [[ -f "$TEST_DIR/.gemini/settings.json" ]] && echo_pass ".gemini/settings.json 생성됨" || echo_fail ".gemini/settings.json 없음"
    [[ -d "$TEST_DIR/.codex/rules" ]] && echo_pass ".codex/rules/ 생성됨" || echo_fail ".codex/rules/ 없음"
    [[ -d "$TEST_DIR/.codex/tools" ]] && echo_pass ".codex/tools/ 생성됨" || echo_fail ".codex/tools/ 없음"
    [[ -d "$TEST_DIR/docs" ]] && echo_pass "docs/ 생성됨" || echo_fail "docs/ 없음"
}

test_codex_only_install() {
    setup_test "codex_only_install"
    
    run_install --codex > /dev/null
    
    # Codex CLI 파일만 있어야 함
    [[ -f "$TEST_DIR/AGENTS.md" ]] && echo_pass "AGENTS.md 생성됨" || echo_fail "AGENTS.md 없음"
    [[ -f "$TEST_DIR/.codex/AGENTS.md" ]] && echo_pass ".codex/AGENTS.md 생성됨" || echo_fail ".codex/AGENTS.md 없음"
    [[ -f "$TEST_DIR/.codex/config.toml" ]] && echo_pass ".codex/config.toml 생성됨" || echo_fail ".codex/config.toml 없음"
    
    # Gemini CLI 파일은 없어야 함
    [[ ! -f "$TEST_DIR/GEMINI.md" ]] && echo_pass "GEMINI.md 없음 (정상)" || echo_fail "GEMINI.md 있음 (비정상)"
    [[ ! -d "$TEST_DIR/.gemini" ]] && echo_pass ".gemini/ 없음 (정상)" || echo_fail ".gemini/ 있음 (비정상)"
}

test_gemini_only_install() {
    setup_test "gemini_only_install"
    
    run_install --gemini > /dev/null
    
    # Gemini CLI 파일만 있어야 함
    [[ -f "$TEST_DIR/GEMINI.md" ]] && echo_pass "GEMINI.md 생성됨" || echo_fail "GEMINI.md 없음"
    [[ -f "$TEST_DIR/.gemini/settings.json" ]] && echo_pass ".gemini/settings.json 생성됨" || echo_fail ".gemini/settings.json 없음"
    
    # Codex CLI 전용 파일은 없어야 함
    [[ ! -f "$TEST_DIR/AGENTS.md" ]] && echo_pass "AGENTS.md 없음 (정상)" || echo_fail "AGENTS.md 있음 (비정상)"
    [[ ! -f "$TEST_DIR/.codex/config.toml" ]] && echo_pass ".codex/config.toml 없음 (정상)" || echo_fail ".codex/config.toml 있음 (비정상)"
}

test_agents_md_pointer_content() {
    setup_test "agents_md_pointer_content"
    
    run_install --codex > /dev/null
    
    # Root AGENTS.md가 포인터인지 확인
    if grep -q "./.codex/AGENTS.md" "$TEST_DIR/AGENTS.md"; then
        echo_pass "AGENTS.md에 ./.codex/AGENTS.md 경로 포함"
    else
        echo_fail "AGENTS.md에 포인터 경로 없음"
    fi
    
    if grep -q "./.codex/rules/00-core.md" "$TEST_DIR/AGENTS.md"; then
        echo_pass "AGENTS.md에 rules 경로 포함"
    else
        echo_fail "AGENTS.md에 rules 경로 없음"
    fi
    
    # .codex/AGENTS.md가 실제 내용을 가지는지 확인
    if grep -q "v2.4.2" "$TEST_DIR/.codex/AGENTS.md"; then
        echo_pass ".codex/AGENTS.md에 버전 정보 포함"
    else
        echo_fail ".codex/AGENTS.md에 버전 정보 없음"
    fi
}

test_gemini_md_import_syntax() {
    setup_test "gemini_md_import_syntax"
    
    run_install --gemini > /dev/null
    
    # GEMINI.md가 @import 문법을 사용하는지 확인
    if grep -q "@./.codex/rules/00-core.md" "$TEST_DIR/GEMINI.md"; then
        echo_pass "GEMINI.md에 @import 문법 사용"
    else
        echo_fail "GEMINI.md에 @import 문법 없음"
    fi
}

test_skip_existing_files() {
    setup_test "skip_existing_files"
    
    # 먼저 설치
    run_install --all > /dev/null
    
    # 사용자 정의 내용으로 AGENTS.md 수정
    echo "# 사용자 정의 AGENTS.md" > "$TEST_DIR/AGENTS.md"
    
    # skip 모드로 재설치
    run_install --all --skip > /dev/null
    
    # 사용자 정의 내용이 유지되는지 확인
    if grep -q "사용자 정의" "$TEST_DIR/AGENTS.md"; then
        echo_pass "skip 모드에서 기존 AGENTS.md 유지됨"
    else
        echo_fail "skip 모드에서 AGENTS.md 덮어씀"
    fi
}

test_mcp_config_content() {
    setup_test "mcp_config_content"
    
    run_install --all > /dev/null
    
    # Codex config.toml에 MCP 설정 있는지 확인
    if grep -q "mcp_servers.local-search" "$TEST_DIR/.codex/config.toml"; then
        echo_pass "config.toml에 local-search MCP 설정 포함"
    else
        echo_fail "config.toml에 MCP 설정 없음"
    fi
    
    # Gemini settings.json에 MCP 설정 있는지 확인
    if grep -q "local-search" "$TEST_DIR/.gemini/settings.json"; then
        echo_pass "settings.json에 local-search MCP 설정 포함"
    else
        echo_fail "settings.json에 MCP 설정 없음"
    fi
}

test_local_search_files() {
    setup_test "local_search_files"
    
    run_install --all > /dev/null
    
    # local-search 도구 파일 확인
    [[ -f "$TEST_DIR/.codex/tools/local-search/mcp/server.py" ]] && echo_pass "server.py 존재" || echo_fail "server.py 없음"
    [[ -f "$TEST_DIR/.codex/tools/local-search/app/db.py" ]] && echo_pass "db.py 존재" || echo_fail "db.py 없음"
    [[ -f "$TEST_DIR/.codex/tools/local-search/README.md" ]] && echo_pass "local-search README 존재" || echo_fail "local-search README 없음"
}

test_rules_directory() {
    setup_test "rules_directory"
    
    run_install --all > /dev/null
    
    # rules 디렉토리 내용 확인
    [[ -f "$TEST_DIR/.codex/rules/00-core.md" ]] && echo_pass "00-core.md 존재" || echo_fail "00-core.md 없음"
}

test_relative_paths_in_pointer() {
    setup_test "relative_paths_in_pointer"
    
    run_install --codex > /dev/null
    
    # 절대경로가 아닌 상대경로 (./) 사용 확인
    if grep -q '\./' "$TEST_DIR/AGENTS.md" && ! grep -q '~/' "$TEST_DIR/AGENTS.md"; then
        echo_pass "AGENTS.md에 상대경로(./) 사용"
    else
        echo_fail "AGENTS.md에 상대경로 미사용 또는 홈 경로(~/) 사용"
    fi
}

test_update_mode_install() {
    setup_test "update_mode_install"

    # 1. Initial Install
    run_install --all > /dev/null

    # 2. Modify files (simulate user changes)
    echo "# User Modified Doc" > "$TEST_DIR/docs/user_doc.md"
    echo "# User Modified GEMINI" > "$TEST_DIR/GEMINI.md"
    # Modify a rule (to see if it gets reverted)
    echo "# Modified Rule" > "$TEST_DIR/.codex/rules/00-core.md"

    # 3. Run Update
    run_install --update > /dev/null

    # 4. Verify Preservation
    if [[ -f "$TEST_DIR/docs/user_doc.md" ]]; then
        echo_pass "Update 모드에서 docs/ 유지됨"
    else
        echo_fail "Update 모드에서 docs/ 삭제됨"
    fi

    if grep -q "User Modified GEMINI" "$TEST_DIR/GEMINI.md"; then
        echo_pass "Update 모드에서 GEMINI.md 유지됨"
    else
        echo_fail "Update 모드에서 GEMINI.md 덮어씌워짐"
    fi

    # 5. Verify Update (Rules should be reset)
    # Note: install.sh copies from source. If source is local script dir, it has original 00-core.md.
    # The modified rule in target should be overwritten by source.
    if ! grep -q "Modified Rule" "$TEST_DIR/.codex/rules/00-core.md"; then
        echo_pass "Update 모드에서 Rules 업데이트됨 (덮어쓰기 성공)"
    else
        echo_fail "Update 모드에서 Rules 업데이트 안됨 (덮어쓰기 실패)"
    fi
}

# =============================================================================
# 메인 실행
# =============================================================================

main() {
    echo "=============================================="
    echo " Codex-Forge install.sh 테스트"
    echo "=============================================="
    echo ""
    
    cleanup
    mkdir -p "$TEST_BASE"
    
    test_basic_all_install
    echo ""
    
    test_codex_only_install
    echo ""
    
    test_gemini_only_install
    echo ""
    
    test_agents_md_pointer_content
    echo ""
    
    test_gemini_md_import_syntax
    echo ""
    
    test_skip_existing_files
    echo ""
    
    test_mcp_config_content
    echo ""
    
    test_local_search_files
    echo ""
    
    test_rules_directory
    echo ""
    
    test_relative_paths_in_pointer
    echo ""

    test_update_mode_install
    echo ""
    
    echo "=============================================="
    echo " 결과: ${GREEN}PASS: $PASS_COUNT${NC} / ${RED}FAIL: $FAIL_COUNT${NC}"
    echo "=============================================="
    
    cleanup
    
    if [[ $FAIL_COUNT -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
