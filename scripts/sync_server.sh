#!/bin/bash
# sync_server.sh — 将本地修改同步到 AutoDL 服务器
#
# 用法：
#   bash scripts/sync_server.sh              # 同步所有代码（pipeline + scripts + training + Paper2Code + aider）
#   bash scripts/sync_server.sh --init       # 首次部署：同步所有 + 创建目录结构 + 迁移旧数据
#   bash scripts/sync_server.sh --pipeline   # 仅同步 pipeline/（快速更新）
#   bash scripts/sync_server.sh --codes      # 仅同步 Paper2Code/codes/（修改了上游脚本时）
#   bash scripts/sync_server.sh --scripts    # 仅同步 scripts/（脚本文件更新）
#   bash scripts/sync_server.sh --logs       # 仅同步 logs/（工作日志）
#
# 环境变量：
#   SERVER_PORT  AutoDL SSH 端口（默认 42345）
#   SERVER_HOST  AutoDL 公网 IP（默认 connect.bjb1.seetacloud.com）
#   SERVER_USER  远端用户（默认 root）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVER_PORT="${SERVER_PORT:-42345}"
SERVER_HOST="${SERVER_HOST:-connect.bjb1.seetacloud.com}"
SERVER_USER="${SERVER_USER:-root}"
REMOTE="${SERVER_USER}@${SERVER_HOST}"
REMOTE_ROOT="/root/paper2XAgent"

MODE="default"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --init)     MODE="init"; shift ;;
        --pipeline) MODE="pipeline"; shift ;;
        --codes)    MODE="codes"; shift ;;
        --scripts)  MODE="scripts"; shift ;;
        --logs)     MODE="logs"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

echo "=== Syncing to ${REMOTE}:${REMOTE_ROOT} (port ${SERVER_PORT}) ==="

# ─── 1. 核心 pipeline 脚本 ───────────────────────────────────────────────
echo "[1/6] Syncing pipeline/*.py ..."
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/pipeline/build_xkg.py" \
    "$REPO_ROOT/pipeline/validate_xkg.py" \
    "$REPO_ROOT/pipeline/qwen_infer.py" \
    "$REPO_ROOT/pipeline/coding_inject.py" \
    "$REPO_ROOT/pipeline/refine_repo.py" \
    "${REMOTE}:${REMOTE_ROOT}/pipeline/"
echo "  ✓ pipeline/*.py synced"

# ─── 2. 测试文件 ─────────────────────────────────────────────────────────
echo "[2/6] Syncing pipeline/tests/ ..."
ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/pipeline/tests"
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/pipeline/tests/test_build_xkg.py" \
    "$REPO_ROOT/pipeline/tests/test_e2e_pipeline.py" \
    "$REPO_ROOT/pipeline/tests/README.md" \
    "${REMOTE}:${REMOTE_ROOT}/pipeline/tests/"
echo "  ✓ pipeline/tests/ synced"

# ─── 3. Paper2Code/codes/（我们修改了 3_coding.py 和 4_debugging.py）──────
echo "[3/6] Syncing Paper2Code/codes/ ..."
ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/Paper2Code/codes"
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/Paper2Code/codes/0_pdf_process.py" \
    "$REPO_ROOT/Paper2Code/codes/1_planning.py" \
    "$REPO_ROOT/Paper2Code/codes/1_planning_llm.py" \
    "$REPO_ROOT/Paper2Code/codes/1.1_extract_config.py" \
    "$REPO_ROOT/Paper2Code/codes/1.2_rag_config.py" \
    "$REPO_ROOT/Paper2Code/codes/2_analyzing.py" \
    "$REPO_ROOT/Paper2Code/codes/2_analyzing_llm.py" \
    "$REPO_ROOT/Paper2Code/codes/3_coding.py" \
    "$REPO_ROOT/Paper2Code/codes/3_coding_llm.py" \
    "$REPO_ROOT/Paper2Code/codes/3.1_coding_sh.py" \
    "$REPO_ROOT/Paper2Code/codes/4_debugging.py" \
    "$REPO_ROOT/Paper2Code/codes/eval.py" \
    "$REPO_ROOT/Paper2Code/codes/utils.py" \
    "${REMOTE}:${REMOTE_ROOT}/Paper2Code/codes/"
echo "  ✓ Paper2Code/codes/ synced"

# ─── 4. Paper2Code/data/paper2code/（data_cleaner.py + cleaned_output）────
echo "[4/6] Syncing Paper2Code/data/paper2code/ ..."
ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/Paper2Code/data/paper2code/cleaned_output"
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/Paper2Code/data/paper2code/data_cleaner.py" \
    "${REMOTE}:${REMOTE_ROOT}/Paper2Code/data/paper2code/"
# 同步 cleaned_output（如果本地有的话）
if ls "$REPO_ROOT/Paper2Code/data/paper2code/cleaned_output/"*.txt 1>/dev/null 2>&1; then
    scp -P "$SERVER_PORT" \
        "$REPO_ROOT/Paper2Code/data/paper2code/cleaned_output/"*.txt \
        "${REMOTE}:${REMOTE_ROOT}/Paper2Code/data/paper2code/cleaned_output/"
    echo "  ✓ Paper2Code/data/paper2code/ synced (with cleaned_output)"
else
    echo "  ✓ Paper2Code/data/paper2code/ synced (no cleaned_output locally)"
fi

if [[ "$MODE" == "pipeline" ]]; then
    echo ""
    echo "=== Done (pipeline mode). ==="
    exit 0
fi

if [[ "$MODE" == "codes" ]]; then
    echo ""
    echo "=== Done (codes mode). ==="
    exit 0
fi

if [[ "$MODE" == "scripts" ]]; then
    echo ""
    echo "[SCRIPTS] Syncing scripts/ only ..."
    ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/scripts"
    scp -P "$SERVER_PORT" \
        "$REPO_ROOT/scripts/run_pipeline.sh" \
        "$REPO_ROOT/scripts/sync_server.sh" \
        "$REPO_ROOT/scripts/fix_server_deps.sh" \
        "${REMOTE}:${REMOTE_ROOT}/scripts/"
    echo "  [OK] scripts/ synced"
    echo ""
    echo "=== Done (scripts mode). ==="
    exit 0
fi

if [[ "$MODE" == "logs" ]]; then
    echo ""
    echo "[LOGS] Syncing logs/ only ..."
    ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/logs"
    scp -P "$SERVER_PORT" \
        "$REPO_ROOT/logs/"*.md \
        "${REMOTE}:${REMOTE_ROOT}/logs/" 2>/dev/null || echo "  [WARN] No .md files in logs/"
    echo "  [OK] logs/ synced"
    echo ""
    echo "=== Done (logs mode). ==="
    exit 0
fi

# ─── 5. scripts/ + training/ ─────────────────────────────────────────────
echo "[5/6] Syncing scripts/ + training/ ..."
ssh -p "$SERVER_PORT" "$REMOTE" "mkdir -p ${REMOTE_ROOT}/scripts ${REMOTE_ROOT}/training"
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/scripts/run_pipeline.sh" \
    "$REPO_ROOT/scripts/fix_server_deps.sh" \
    "${REMOTE}:${REMOTE_ROOT}/scripts/"
scp -P "$SERVER_PORT" \
    "$REPO_ROOT/training/train_qwen.yaml" \
    "$REPO_ROOT/training/merge_qwen.yaml" \
    "$REPO_ROOT/training/serve_vllm.sh" \
    "$REPO_ROOT/training/run_inference.sh" \
    "$REPO_ROOT/training/inference.py" \
    "${REMOTE}:${REMOTE_ROOT}/training/"
echo "  ✓ scripts/ + training/ synced"

# ─── 6. aider/（Stage 5 refine_repo.py 需要）─────────────────────────────
echo "[6/6] Syncing aider/ ..."
# 用 tar + ssh 传输目录（比 scp -r 更可靠，且可排除不需要的文件）
tar -C "$REPO_ROOT" --exclude='aider/.git' --exclude='aider/__pycache__' --exclude='aider/*.egg-info' \
    -cf - aider/ | ssh -p "$SERVER_PORT" "$REMOTE" "tar -C ${REMOTE_ROOT} -xf -"
echo "  ✓ aider/ synced"

# ─── 清理旧文件 ──────────────────────────────────────────────────────────
echo ""
echo "Cleaning up old files on server ..."
ssh -p "$SERVER_PORT" "$REMOTE" bash <<'CLEANUP'
    ROOT="/root/paper2XAgent"
    # 删除旧位置的 run_pipeline.sh（已移至 scripts/）
    if [[ -f "$ROOT/pipeline/run_pipeline.sh" ]]; then
        rm "$ROOT/pipeline/run_pipeline.sh"
        echo "  ✓ Removed old pipeline/run_pipeline.sh"
    fi
    # 删除旧位置的 test_build_xkg.py（已移至 tests/）
    if [[ -f "$ROOT/pipeline/test_build_xkg.py" ]]; then
        rm "$ROOT/pipeline/test_build_xkg.py"
        echo "  ✓ Removed old pipeline/test_build_xkg.py"
    fi
CLEANUP

# ─── 初始化模式：创建目录 + 迁移旧数据 ────────────────────────────────────
if [[ "$MODE" == "init" ]]; then
    echo ""
    echo "=== INIT: Creating output directories & migrating old data ==="

    ssh -p "$SERVER_PORT" "$REMOTE" bash <<'REMOTE_SCRIPT'
        set -euo pipefail
        ROOT="/root/paper2XAgent"

        # 创建新目录结构
        mkdir -p "$ROOT/outputs/qwen" "$ROOT/outputs/xkg" "$ROOT/outputs/repos"

        # 迁移旧数据（如果存在）
        if [[ -d "$ROOT/qwen_outputs" ]]; then
            echo "  Migrating qwen_outputs/ → outputs/qwen/"
            cp -rn "$ROOT/qwen_outputs/"* "$ROOT/outputs/qwen/" 2>/dev/null || true
        fi

        if [[ -d "$ROOT/xkg" ]]; then
            echo "  Migrating xkg/ → outputs/xkg/"
            cp -rn "$ROOT/xkg/"* "$ROOT/outputs/xkg/" 2>/dev/null || true
        fi

        # 将根目录的 cleaned_output 移到正确位置
        if [[ -d "$ROOT/cleaned_output" ]] && [[ -d "$ROOT/Paper2Code/data/paper2code" ]]; then
            echo "  Moving cleaned_output/ → Paper2Code/data/paper2code/cleaned_output/"
            cp -rn "$ROOT/cleaned_output/"* "$ROOT/Paper2Code/data/paper2code/cleaned_output/" 2>/dev/null || true
        fi

        echo "  ✓ Directory structure created"
REMOTE_SCRIPT
fi

echo ""
echo "=== Done. ==="
