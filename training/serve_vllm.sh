#!/bin/bash
# serve_vllm.sh — 在 AutoDL 服务器上用 vLLM 启动 OpenAI-compatible API
#
# 启动后，本地（通过端口转发）调用：
#   base_url = "http://localhost:8000/v1"
#   model    = "qwen-paper2code"
#   api_key  = "sk-local-any-string"
#
# 端口转发命令（在本地机器运行）：
#   ssh -L 8000:localhost:8000 root@<autodl公网IP> -p <端口号>

source /root/anaconda3/etc/profile.d/conda.sh
conda activate base

export HF_HOME="/root/autodl-tmp/huggingface_cache"
export CUDA_VISIBLE_DEVICES=0

MODEL_DIR="/root/autodl-tmp/Qwen2.5-7B-paper2Xcode"

if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 模型目录不存在: $MODEL_DIR"
    exit 1
fi

# 检查 vllm 是否安装
if ! python -c "import vllm" 2>/dev/null; then
    echo "vllm 未安装，正在安装..."
    pip install vllm -q
fi

echo "✅ 启动 vLLM 服务..."
echo "   模型: $MODEL_DIR"
echo "   端口: 8000"
echo "   按 Ctrl+C 停止"

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_DIR" \
    --served-model-name "qwen-paper2code" \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 4096 \
    --trust-remote-code
