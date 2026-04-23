#!/bin/bash
# fix_server_deps.sh — 修复服务器端 Python 依赖问题
#
# 重要：必须在 llama 环境下运行（服务器有 CUDA 驱动）
#   conda activate llama
#   bash scripts/fix_server_deps.sh
#
# 用法（在服务器上运行）：
#   bash scripts/fix_server_deps.sh
#
# 功能：
#   1. 升级 openai 库到最新版本（使用预编译轮子，避免 JSON 解析错误）
#   2. 安装 pipeline/requirements.txt 中的所有依赖
#   3. 验证关键导入是否正常

set -euo pipefail

echo "========================================"
echo "Fixing server dependencies"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS="$REPO_ROOT/pipeline/requirements.txt"

# 检查 requirements.txt 是否存在
if [[ ! -f "$REQUIREMENTS" ]]; then
    echo "[ERROR] requirements.txt not found at: $REQUIREMENTS"
    exit 1
fi

echo ""
echo "--- Step 1: Upgrading openai library (with prebuilt wheels) ---"
echo "[INFO] Using prebuilt wheels to avoid JSON parsing errors"

# 使用预编译轮子安装（跳过依赖解析，避免 JSON 错误）
pip install --upgrade openai \
    --prefer-binary \
    --no-deps \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 补充安装 openai 的必要依赖
pip install httpx anyio distro tqdm typing-extensions \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

echo ""
echo "--- Step 2: Installing all pipeline dependencies ---"
pip install -r "$REQUIREMENTS"

echo ""
echo "--- Step 3: Verifying imports ---"

# 验证 OpenAI 导入
python3 <<'EOF'
try:
    from openai import OpenAI
    print("[OK] OpenAI import successful")
except ImportError as e:
    print(f"[ERROR] OpenAI import failed: {e}")
    exit(1)
EOF

# 验证其他关键导入
python3 <<'EOF'
import sys
errors = []

try:
    import numpy
    print("[OK] numpy")
except ImportError:
    errors.append("numpy")

try:
    import sentence_transformers
    print("[OK] sentence_transformers")
except ImportError:
    print("[WARN] sentence_transformers not installed (optional)")

try:
    import faiss
    print("[OK] faiss")
except ImportError:
    print("[WARN] faiss not installed (optional, will use numpy fallback)")

if errors:
    print(f"\n[ERROR] Missing required packages: {', '.join(errors)}")
    sys.exit(1)
EOF

echo ""
echo "========================================"
echo "[OK] All dependencies fixed!"
echo "========================================"
echo ""
echo "Next: Run the e2e test again:"
echo "  cd ~/paper2XAgent"
echo "  python pipeline/tests/test_e2e_pipeline.py --mock-llm"
