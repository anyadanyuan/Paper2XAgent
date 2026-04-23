import os
import sys
import logging

# 设置日志输出到文件
logging.basicConfig(
    level=logging.INFO,
    filename="generation.log",
    encoding="utf-8",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# 同时输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console_handler)

# 设置 API key - 使用 OpenRouter
# ⚠️ 请设置环境变量或从配置文件读取
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

logging.info("Starting dataset generation...")

# 测试 API key
logging.info(f"API Key starts with: {os.environ.get('OPENAI_API_KEY', '')[:15]}...")

try:
    from distill_code_repository import GitExtractor, CostEstimator, DistillationEngine

    # 测试 API 连接
    logging.info("Testing API connection...")
    test_client = DistillationEngine(
        prompt_file_path="distill_code_repository_system_prompt.md"
    )
    logging.info("API connection successful!")
except Exception as e:
    logging.error(f"Error during initialization: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
