import os
import re
import json
import tempfile
import subprocess
import tiktoken
from openai import OpenAI
from typing import List, Dict


class CostEstimator:
    """成本核算专家：精准计算 Token 并预估美元花费"""

    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.encoding = tiktoken.encoding_for_model(self.model_name)

        # GPT-4o 的官方 API 价格（请根据最新官方定价调整，这里假设为 $5/1M input, $15/1M output）
        self.price_per_1k_input = 0.005
        self.price_per_1k_output = 0.015

    def count_tokens(self, text: str) -> int:
        """计算一段文本的精确 Token 数"""
        return len(self.encoding.encode(text))

    def estimate_cost(
        self, input_tokens: int, estimated_output_tokens: int = 1500
    ) -> float:
        """根据 Token 数量预估美元花费"""
        input_cost = (input_tokens / 1000) * self.price_per_1k_input
        output_cost = (estimated_output_tokens / 1000) * self.price_per_1k_output
        return input_cost + output_cost


class GitExtractor:
    """Git 提取引擎：阅后即焚模式"""

    @staticmethod
    def extract_python_code(repo_url: str) -> str:
        """克隆仓库，提取所有 .py 文件并合并，最后自动清理痕迹"""
        merged_code = []

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"正在克隆 {repo_url} 到临时目录 {temp_dir} ...")

            # 设置环境变量以避免 git 警告
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GCM_INTERACTIVE"] = "never"
            env["CI"] = "true"

            # 提示：为了加快速度，建议加上 --depth 1 参数只克隆最后一次 commit
            # 使用 shell=True 在 Windows 上避免路径问题
            result = subprocess.run(
                f'git clone --depth 1 "{repo_url}" "{temp_dir}"',
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                print(f"Git clone stderr: {result.stderr}")

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                code_content = f.read()
                                # 加上明显的分隔符和文件名，方便大模型识别
                                merged_code.append(
                                    f"\n\n# {'=' * 20}\n# FILE: {file}\n# {'=' * 20}\n{code_content}"
                                )
                        except Exception as e:
                            pass

        return "".join(merged_code)


class DistillationEngine:
    def __init__(self, prompt_file_path: str, model_name: str = "gpt-4o"):
        # 支持 OpenRouter (sk-or-v1-xxx) 和 OpenAI API
        api_key = os.environ.get("OPENAI_API_KEY", "")
        print(f"API Key loaded: {api_key[:20]}..." if api_key else "No API key found!")

        if api_key.startswith("sk-or-v1-"):
            # OpenRouter 需要设置 base_url
            print("Using OpenRouter...")
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1", api_key=api_key
            )
            # OpenRouter 上使用 gpt-4o-mini 更经济
            self.model_name = "gpt-4o-mini"
        else:
            print("Using standard OpenAI API...")
            self.client = OpenAI(api_key=api_key)
            self.model_name = model_name

        with open(prompt_file_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def distill_code(self, raw_repo_code: str) -> str:
        """调用最新接口提纯代码，并做正则防御"""
        full_input = f"{self.system_prompt}\n\n[REPOSITORY CODE]:\n{raw_repo_code}"

        # 使用 2026 最新官方 SDK 语法
        response = self.client.responses.create(
            model=self.model_name,
            input=full_input,
            # tools=[], # 注意：千万不要加 web_search 工具！
        )
        llm_raw_output = response.output_text

        # 防御性编程：用正则表达式强行提取 <file> 标签内的内容
        matches = re.findall(
            r'(<file name=".*?">.*?</file>)', llm_raw_output, flags=re.DOTALL
        )
        if matches:
            return "\n\n".join(matches)
        else:
            print("⚠️ 警告：模型未输出 file 标签！返回原始文本。")
            return llm_raw_output
