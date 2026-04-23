#!/bin/bash

# 1. 强制激活环境 (根据你之前的 Conda 情况)
# 即使 ~/.bashrc 写了，脚本里显式 source 一次更保险
source /root/anaconda3/etc/profile.d/conda.sh
conda activate base

# 2. 核心路径变量（这就是你的“代码品味”：将配置与逻辑分离）
MODEL_DIR="/root/autodl-tmp/Qwen2.5-7B-paper2Xcode"
SCRIPT_PATH="/root/LLaMA-Factory/firstAttempt/inference.py" # 建议放在数据盘

# 3. 环境变量最后一次加固（防止爆系统盘的最后一道防线）
export HF_HOME="/root/autodl-tmp/huggingface_cache"
export PIP_CACHE_DIR="/root/autodl-tmp/pip_cache"
export CUDA_VISIBLE_DEVICES=0  # 指定只用第一块显卡

# 4. 运行前安检
echo "--- Starting Pre-flight Checks ---"
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 错误: 找不到模型文件夹 $MODEL_DIR"
    exit 1
fi

# 检查系统盘剩余空间（如果小于 1G 报警）
FREE_SPACE=$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$FREE_SPACE < 1.0" | bc -l) )); then
    echo "⚠️ 警告: 系统盘空间仅剩 ${FREE_SPACE}G，请清理后再运行！"
    # exit 1 # 如果你想强制停止可以取消注释
fi
echo "--- Pre-flight Checks Passed ---"

# 5. 执行推理
# 使用 python -u (unbuffered) 可以实时看到 Python 的 print 输出
python -u "$SCRIPT_PATH"
