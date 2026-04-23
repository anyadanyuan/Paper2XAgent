"""
build_xkg.py — Stage 2 of paper2XAgent pipeline

当前实现（简化版）：直接将 Qwen-7B SFT 输出解析为 xKG JSON，
每个 <file> 标签对应一个 Technique 节点，不做 LLM 技术提取和代码检索。

扩展接口：CodeProvider ABC 供日后接入多论文语料库检索
（即 xKG 论文 Section 2.2 的完整 Hierarchical KG Construction 流程）。

Usage:
  python pipeline/build_xkg.py \\
      --paper_name AttentionCalibration \\
      --paper_txt  cleaned_output/AttentionCalibration.txt \\
      --qwen_output outputs/qwen/AttentionCalibration.xml \\
      --output_dir  outputs/xkg/
"""

from __future__ import annotations

import argparse
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


# =============================================================================
# xKG 数据结构（保持与原始 xKG 论文 Figure 6 格式一致）
# =============================================================================

def make_code_node(implementation: str, documentation: str = "") -> dict:
    """构造 Code Node：{implementation, documentation, package}"""
    return {
        "implementation": implementation,
        "documentation": documentation,
        "package": _extract_packages(implementation),
    }


def make_technique_node(
    name: str,
    description: str,
    code: dict,
    tech_type: str = "Methodology",
    components: Optional[list] = None,
    verified: Optional[bool] = None,
) -> dict:
    """
    构造 Technique Node。

    verified=None  表示尚未经过沙盒验证（由 validate_xkg.py 填充）
    verified=True  表示已通过沙盒验证
    verified=False 表示验证失败（已被 validate_xkg.py 尝试修复但失败，待剪枝）
    """
    node: dict = {
        "name": name,
        "type": tech_type,
        "description": description,
        "components": components or [],
        "code": code,
    }
    if verified is not None:
        node["verified"] = verified
    return node


def make_xkg(paper_title: str, abstract: str, techniques: list[dict]) -> dict:
    """构造顶层 xKG JSON"""
    return {
        "paper_title": paper_title,
        "abstract": abstract,
        "techniques": techniques,
    }


# =============================================================================
# 扩展接口：CodeProvider
# =============================================================================

class CodeProvider(ABC):
    """
    代码来源的抽象接口。

    当前实现：QwenOutputProvider  — 解析 Qwen-7B XML 输出（单文件场景）

    未来扩展：CorpusRAGProvider   — 从多篇参考论文的 GitHub 仓库检索，
                                    复现 xKG 论文 Section 2.2 完整流程：
                                    Technique Extraction → Code RAG → Rewrite → Verify
    """

    @abstractmethod
    def provide(self, paper_title: str, paper_text: str) -> dict[str, str]:
        """
        返回 {filename: code_text} 字典。
        每个 key-value 对对应一个独立的算法模块。
        paper_text 供有检索需求的子类使用（当前实现中忽略）。
        """
        ...

    def describe(self) -> str:
        """返回来源描述，写入 xKG JSON 供审计追踪"""
        return self.__class__.__name__


# =============================================================================
# 当前实现：QwenOutputProvider
# =============================================================================

class QwenOutputProvider(CodeProvider):
    """
    从 Qwen-7B SFT 输出的 XML 格式中解析代码文件。

    期望输入格式：
        <file name="core_model.py">
        import torch
        ...
        </file>

    若无 <file> 标签（旧版模型输出），整段内容作为 core_model.py。
    """

    def __init__(self, qwen_xml: str):
        self._xml = qwen_xml

    def provide(self, paper_title: str, paper_text: str) -> dict[str, str]:
        matches = re.findall(r'<file name="([^"]+)">(.*?)</file>', self._xml, re.DOTALL)
        if matches:
            return {name: code.strip() for name, code in matches}
        print("[QwenOutputProvider] No <file> tags in output, treating as core_model.py")
        return {"core_model.py": self._xml.strip()}

    def describe(self) -> str:
        return "QwenOutputProvider (Qwen2.5-Coder-7B SFT)"


# =============================================================================
# 未来扩展占位符
# =============================================================================

class CorpusRAGProvider(CodeProvider):
    """
    TODO: 多论文语料库检索，复现 xKG 论文原始方案。

    实现步骤（参考论文 Section 2.2.2 + Appendix E）：

    Step 1 — Technique Extraction（prompts/technique_extraction.md）
        LLM 从目标论文提取技术节点层次树（Methodology / Technique / Finding / Resource）
        + Paper-RAG（chunk_size=350, top_k=5）丰富各节点描述

    Step 2 — Code Modularization
        a. 对每个 Technique 节点：
           - FAISS 检索相关代码 chunks（chunk_size=350, overlap=100, top_k=10）
           - LLM re-rank 选出最相关文件（top_files=5）
           （prompts/code_file_selection.md）
        b. LLM 将代码片段改写为自包含 Code Node（含 # TEST BLOCK）
           叶节点：prompts/code_rewrite_leaf.md
           复合节点：prompts/code_rewrite_composite.md
        c. LLM 验证代码是否忠实于技术描述
           （prompts/code_verify.md）

    Step 3 — Knowledge Filtering
        删除无法检索到代码的 Technique 节点

    所需外部资源：
        corpus   : list[dict]   每篇参考论文的 {paper_text, github_url, file_dict}
        client   : OpenAI       LLM 调用（建议 o4-mini 或 gpt-4.1-mini）
        embedder : EmbeddingModel  text-embedding-3-small 或 all-MiniLM-L6-v2

    超参数（来自 xKG 论文 Table 9-12）：
        code.chunk_size=350, code.chunk_overlap=100, code.faiss.top_k=10
        code.llm.top_files=5，paper.chunk_size=350, paper.faiss.top_k=5
        retrieve.embedding_model=all-MiniLM-L6-v2, retrieve.similarity=0.6
    """

    def __init__(self, corpus: list[dict], client, embedder):
        raise NotImplementedError(
            "CorpusRAGProvider is a planned future extension.\n"
            "Use QwenOutputProvider for the current single-paper workflow."
        )

    def provide(self, paper_title: str, paper_text: str) -> dict[str, str]:
        raise NotImplementedError


# =============================================================================
# 工具函数
# =============================================================================

_STDLIB = {
    "os", "sys", "re", "json", "math", "time", "copy", "random", "abc",
    "typing", "pathlib", "collections", "functools", "itertools",
    "dataclasses", "logging", "warnings", "io", "string", "hashlib",
    "inspect", "contextlib", "threading", "subprocess", "tempfile",
    "enum", "struct", "pickle", "shutil", "glob", "argparse",
}


def _extract_packages(code: str) -> list[str]:
    packages: set[str] = set()
    for line in code.splitlines():
        line = line.strip()
        m = re.match(r"^import\s+([\w]+)", line)
        if m:
            packages.add(m.group(1))
        m = re.match(r"^from\s+([\w]+)", line)
        if m:
            packages.add(m.group(1))
    return sorted(packages - _STDLIB)


def _extract_abstract(paper_text: str) -> str:
    m = re.search(r"\[Abstract\]\n(.*?)(?:\n\[|\Z)", paper_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return paper_text[:1000]


def _filename_to_node_name(filename: str) -> str:
    """core_model.py → Core Model"""
    return Path(filename).stem.replace("_", " ").title()


# =============================================================================
# 主流程
# =============================================================================

def build_xkg(
    paper_title: str,
    paper_text: str,
    provider: CodeProvider,
) -> dict:
    """
    构建 xKG JSON。

    Args:
        paper_title : 论文名（作为 xKG 标识符）
        paper_text  : data_cleaner.py 输出的清洗文本
        provider    : CodeProvider 实例

    Returns:
        xKG dict，可直接 json.dump
    """
    print(f"\n{'='*60}")
    print(f"Building xKG for  : {paper_title}")
    print(f"Code provider     : {provider.describe()}")
    print(f"{'='*60}\n")

    abstract = _extract_abstract(paper_text)
    file_dict = provider.provide(paper_title, paper_text)

    print(f"Parsed {len(file_dict)} file(s): {list(file_dict.keys())}")

    techniques: list[dict] = []
    for filename, code in file_dict.items():
        if not code.strip():
            print(f"  [skip] {filename}: empty")
            continue

        node = make_technique_node(
            name=_filename_to_node_name(filename),
            description=(
                f"Core algorithm implementation from {filename}, "
                f"generated by Qwen2.5-Coder-7B SFT for paper '{paper_title}'."
            ),
            code=make_code_node(code),
            tech_type="Methodology" if "model" in filename.lower() else "Technique",
            verified=None,  # validate_xkg.py 填充
        )
        pkgs = node["code"]["package"]
        print(f"  + {node['name']}  ({len(code):,} chars, packages: {pkgs})")
        techniques.append(node)

    print(f"\n[xKG] {len(techniques)} node(s) pending validation by validate_xkg.py")

    return make_xkg(paper_title, abstract, techniques)


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build xKG JSON from Qwen-7B SFT output"
    )
    parser.add_argument("--paper_name", required=True,
                        help="Paper identifier (e.g. AttentionCalibration)")
    parser.add_argument("--paper_txt", required=True,
                        help="Cleaned paper text (output of data_cleaner.py)")

    qwen_group = parser.add_mutually_exclusive_group(required=True)
    qwen_group.add_argument("--qwen_output",
                            help="Path to existing Qwen output .xml file")
    qwen_group.add_argument("--qwen_model_path",
                            help="Qwen model weights path; triggers automatic inference")

    parser.add_argument("--output_dir", default="outputs/xkg",
                        help="Directory to save xKG JSON (default: outputs/xkg/)")
    args = parser.parse_args()

    paper_text = Path(args.paper_txt).read_text(encoding="utf-8")

    if args.qwen_output:
        qwen_xml = Path(args.qwen_output).read_text(encoding="utf-8")
    else:
        print(f"[Qwen] Running inference with: {args.qwen_model_path}")
        from qwen_infer import generate_core_code
        qwen_xml = generate_core_code(
            paper_text=paper_text[:6000],
            model_path=args.qwen_model_path,
        )
        cache_dir = Path(args.output_dir).parent / "qwen"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{args.paper_name}.xml"
        cache_path.write_text(qwen_xml, encoding="utf-8")
        print(f"[Qwen] Output cached to {cache_path}")

    provider = QwenOutputProvider(qwen_xml)
    xkg = build_xkg(
        paper_title=args.paper_name,
        paper_text=paper_text,
        provider=provider,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.paper_name}.json"
    out_path.write_text(json.dumps(xkg, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nxKG saved  : {out_path}")
    print(f"Next step  : python pipeline/validate_xkg.py --xkg_path {out_path}")


if __name__ == "__main__":
    main()
