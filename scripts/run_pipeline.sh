#!/bin/bash
# run_pipeline.sh — paper2XAgent 完整流水线（在服务器上运行）
#
# 流程：
#   Stage 0: data_cleaner.py       → Paper2Code/data/paper2code/cleaned_output/*.txt
#   Stage 1: qwen_infer.py         → outputs/qwen/*.xml   (Qwen2.5-7B 本地推理)
#   Stage 2: build_xkg.py          → outputs/xkg/*.json   (技术提取 + 代码模块化)
#   Stage 3: validate_xkg.py       → outputs/xkg/*_validated.json (沙盒验证 + 自调试)
#
# 用法（服务器上）：
#   bash scripts/run_pipeline.sh --paper AttentionCalibration [--all]
#
# 环境变量：
#   OPENAI_API_KEY   用于 build_xkg / validate_xkg 调用 LLM
#   QWEN_MODEL_PATH  覆盖默认 Qwen 模型路径（可选）

set -euo pipefail

# ── 配置 ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

QWEN_MODEL_PATH="${QWEN_MODEL_PATH:-/root/autodl-tmp/Qwen2.5-7B-paper2Xcode}"
CLEANED_DIR="$REPO_ROOT/Paper2Code/data/paper2code/cleaned_output"
QWEN_OUT_DIR="$REPO_ROOT/outputs/qwen"
XKG_DIR="$REPO_ROOT/outputs/xkg"

EXTRACT_MODEL="gpt-4.1-mini"
CODE_MODEL="gpt-4.1-mini"
DEBUG_MODEL="gpt-4.1-mini"
MAX_DEBUG_ROUNDS=3

# ── 参数解析 ──────────────────────────────────────────────────────────────────
PAPER_NAME=""
RUN_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --paper)   PAPER_NAME="$2"; shift 2 ;;
        --all)     RUN_ALL=true; shift ;;
        --help|-h)
            echo "Usage: $0 --paper <PaperName> [--all]"
            echo "  --paper   Process a single paper by name (stem of .txt file)"
            echo "  --all     Process all papers in cleaned_output/"
            exit 0 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -z "$PAPER_NAME" && "$RUN_ALL" == "false" ]]; then
    echo "❌ Specify --paper <name> or --all"
    exit 1
fi

# ── 检查依赖 ──────────────────────────────────────────────────────────────────
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "❌ OPENAI_API_KEY not set (needed for build_xkg / validate_xkg)"
    exit 1
fi

if [[ ! -d "$QWEN_MODEL_PATH" ]] && [[ -z "${QWEN_API_BASE:-}" ]]; then
    echo "❌ Qwen model not found at $QWEN_MODEL_PATH"
    echo "   Set QWEN_MODEL_PATH or QWEN_API_BASE"
    exit 1
fi

# ── Stage 0: data_cleaner.py ──────────────────────────────────────────────────
echo "========================================"
echo "Stage 0: Cleaning paper JSONs"
echo "========================================"
python "$REPO_ROOT/Paper2Code/data/paper2code/data_cleaner.py"

# ── 获取待处理文件列表 ────────────────────────────────────────────────────────
if [[ "$RUN_ALL" == "true" ]]; then
    PAPERS=()
    for f in "$CLEANED_DIR"/*.txt; do
        PAPERS+=("$(basename "$f" .txt)")
    done
else
    PAPERS=("$PAPER_NAME")
fi

echo "Papers to process: ${PAPERS[*]}"

# ── 逐篇处理 ──────────────────────────────────────────────────────────────────
for NAME in "${PAPERS[@]}"; do
    echo ""
    echo "========================================"
    echo "Processing: $NAME"
    echo "========================================"

    PAPER_TXT="$CLEANED_DIR/${NAME}.txt"
    QWEN_XML="$QWEN_OUT_DIR/${NAME}.xml"
    XKG_JSON="$XKG_DIR/${NAME}.json"
    XKG_VALIDATED="$XKG_DIR/${NAME}_validated.json"

    if [[ ! -f "$PAPER_TXT" ]]; then
        echo "⚠️  $PAPER_TXT not found, skipping"
        continue
    fi

    # Stage 1: Qwen 推理（增量：已有 xml 则跳过）
    echo "--- Stage 1: Qwen Inference ---"
    mkdir -p "$QWEN_OUT_DIR"
    if [[ -f "$QWEN_XML" ]]; then
        echo "  ✓ Already exists: $QWEN_XML (skipping)"
    else
        python "$REPO_ROOT/pipeline/qwen_infer.py" \
            --single "$PAPER_TXT" \
            --model_path "$QWEN_MODEL_PATH" \
            > "$QWEN_XML"
        echo "  ✓ Saved: $QWEN_XML"
    fi

    # Stage 2: build_xkg（增量：已有 json 则跳过）
    echo "--- Stage 2: Build xKG ---"
    mkdir -p "$XKG_DIR"
    if [[ -f "$XKG_JSON" ]]; then
        echo "  ✓ Already exists: $XKG_JSON (skipping)"
    else
        python "$REPO_ROOT/pipeline/build_xkg.py" \
            --paper_name "$NAME" \
            --paper_txt  "$PAPER_TXT" \
            --qwen_output "$QWEN_XML" \
            --output_dir  "$XKG_DIR"
    fi

    # Stage 3: validate_xkg（增量：已有 validated json 则跳过）
    echo "--- Stage 3: Validate xKG ---"
    if [[ -f "$XKG_VALIDATED" ]]; then
        echo "  ✓ Already exists: $XKG_VALIDATED (skipping)"
    else
        python "$REPO_ROOT/pipeline/validate_xkg.py" \
            --xkg_path   "$XKG_JSON" \
            --output_dir "$XKG_DIR" \
            --model      "$DEBUG_MODEL" \
            --max_rounds "$MAX_DEBUG_ROUNDS"
    fi

    echo "✅ $NAME complete"
done

echo ""
echo "========================================"
echo "Pipeline finished"
echo "  Qwen outputs : $QWEN_OUT_DIR"
echo "  xKG JSONs    : $XKG_DIR"
echo "========================================"
