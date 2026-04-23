"""
model_loader.py - 模型加载器

统一加载基座模型或微调模型，支持：
- 本地 transformers 加载
- vLLM / OpenAI-compatible API 调用
"""

from __future__ import annotations

import os
from typing import Optional

import torch


class ModelLoader:
    """统一模型加载器"""

    def __init__(
        self,
        model_path: str,
        use_api: bool = False,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        初始化模型加载器。

        Args:
            model_path: 本地路径或 HuggingFace model_id
            use_api: 是否通过 API 调用（vLLM/OpenAI-compatible）
            api_base: API 地址（如 http://localhost:8000/v1）
            api_key: API 密钥（可选）
        """
        self.model_path = model_path
        self.use_api = use_api
        self.api_base = api_base or "http://localhost:8000/v1"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "EMPTY")

        self.model = None
        self.tokenizer = None
        self.client = None

        if use_api:
            self._init_api()
        else:
            self._init_local()

    def _init_local(self):
        """初始化本地模型加载"""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"[ModelLoader] Loading model from {self.model_path}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True,
        )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        print("[ModelLoader] Model loaded successfully.")

    def _init_api(self):
        """初始化 API 客户端"""
        from openai import OpenAI

        print(f"[ModelLoader] Using API at {self.api_base}")

        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key,
        )

    def generate(
        self,
        paper_text: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        生成代码。

        使用与训练时一致的 Alpaca 格式 prompt。

        Args:
            paper_text: 论文文本（Abstract + Method）
            max_tokens: 最大生成长度
            temperature: 温度参数
            top_p: top_p 参数

        Returns:
            模型生成的输出字符串
        """
        # 构造 Alpaca 格式 prompt
        instruction = (
            "You are an expert in reproducing academic papers into executable code. "
            "Given the paper's abstract and method description, generate the complete "
            "PyTorch implementation of the core model architecture."
        )

        prompt = self._format_alpaca_prompt(instruction, paper_text)

        if self.use_api:
            return self._generate_api(prompt, max_tokens, temperature, top_p)
        else:
            return self._generate_local(prompt, max_tokens, temperature, top_p)

    def _format_alpaca_prompt(self, instruction: str, input_text: str) -> str:
        """
        格式化为 Alpaca prompt 格式。

        与训练时的格式保持一致。
        """
        return (
            f"### Instruction:\n{instruction}\n\n"
            f"### Input:\n{input_text}\n\n"
            f"### Response:\n"
        )

    def _generate_local(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """本地模型生成"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        # 解码，去除 prompt 部分
        full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 提取 Response 之后的部分
        if "### Response:" in full_output:
            response = full_output.split("### Response:")[-1].strip()
        else:
            response = full_output

        return response

    def _generate_api(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """API 模式生成"""
        response = self.client.completions.create(
            model=self.model_path,  # vLLM 使用模型名称
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        return response.choices[0].text.strip()
