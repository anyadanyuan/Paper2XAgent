"""
该脚本用于将paper2code提供的cleaned_json文件进一步清洗，只保留其中涉及算法的部分，以减小输入的token数量。最终输出的每篇论文以txt格式呈现。
"""

import json
from typing import List, Dict, Any


class PaperDataCleaner:
    def __init__(self):
        keywords = {
            "high_importance": {
                "method",
                "methodology",
                "approach",
                "model",
                "architecture",
                "framework",
                "implementation",
                "algorithm",
                "network",
                "encoder",
                "decoder",
                "attention",
                "transformer",
                "layer",
                "module",
                "embedding",
                "loss",
                "objective",
                "training",
                "optimizer",
                "inference",
            },
            "medium_importance": {
                "experiment",
                "experiments",
                "result",
                "results",
                "evaluation",
                "benchmark",
                "dataset",
                "datasets",
                "baseline",
                "baselines",
                "ablation",
                "metric",
                "metrics",
                "performance",
                "accuracy",
                "sensitivity",
                "comparison",
                "setup",
                "setting",
            },
            "low_importance": {
                "introduction",
                "related work",
                "background",
                "conclusion",
                "discussion",
                "preliminaries",
                "limitation",
                "limitations",
                "future work",
                "appendix",
                "supplementary",
                "acknowledgement",
                "ethics",
                "impact",
                "safeguards",
                "reference",
            },
        }
        # 架构师的配置分离：定义我们需要保留的核心章节关键词（转小写以作匹配）
        self.target_keywords = keywords[
            "high_importance"
        ]  # keywords["high_importance"] | keywords["medium_importance"] 当原本的token不多的时候尽量保存多一点
        self.drop_keywords = keywords["low_importance"]

    def _is_useful_section(self, section_name: str) -> bool:
        """
        判断该段落是否是我们需要的核心章节
        注意最终要验证的是section_name是否包含这些关键词而不是是否等于
        """
        if not section_name:
            return False

        sec_lower = section_name.lower()

        # 判断 target_keywords 中是否有任意一个词出现在 sec_lower 中。
        is_target = any(kw in sec_lower for kw in self.target_keywords)

        # 进一步防御性编程：确保它不是我们要丢弃的章节
        is_drop = any(kw in sec_lower for kw in self.drop_keywords)

        return is_target and not is_drop

    def clean_paper(self, raw_json: Dict[str, Any]) -> str:
        """
        将庞大的论文 JSON 压缩为高信息密度的纯文本。
        """
        extracted_texts = []

        # 1. 强行保留 Abstract
        abstract_text = raw_json.get("abstract", "")
        extracted_texts.append(f"[Abstract]\n{abstract_text}\n")

        # 2. 遍历 Body Text，精准抽取核心段落
        body_texts = raw_json.get("pdf_parse", {}).get("body_text", [])

        for paragraph in body_texts:
            sec_name = paragraph.get("section", "")
            text = paragraph.get("text", "")

            # TODO: 调用上面写好的判定函数，如果该段落有用，
            # 则将其按照 f"[{sec_name}] {text}" 的格式追加到 extracted_texts 列表中。
            if self._is_useful_section(sec_name):
                extracted_texts.append(f"[{sec_name}]\n{text}\n")

        # 3. 将列表合并为单一字符串返回
        return "\n".join(extracted_texts)


# 客户端调用示例
# cleaner = PaperDataCleaner()
# clean_input = cleaner.clean_paper(paper_json)


if __name__ == "__main__":
    import os
    import glob
    from tqdm import tqdm

    # 配置路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "..", "paper2code")
    OUTPUT_DIR = os.path.join(BASE_DIR, "cleaned_output")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 查找所有 _cleaned.json 文件
    conferences = ["iclr2024", "icml2024", "nips2024"]
    json_files = []
    for conf in conferences:
        conf_dir = os.path.join(DATA_DIR, conf)
        if os.path.exists(conf_dir):
            pattern = os.path.join(conf_dir, "*_cleaned.json")
            json_files.extend(glob.glob(pattern))

    print(f"找到 {len(json_files)} 个 cleaned_json 文件")
    print("=" * 60)

    # 初始化清洗器
    cleaner = PaperDataCleaner()

    # 统计信息
    total_original_chars = 0
    total_cleaned_chars = 0

    # 逐个处理
    for json_path in tqdm(json_files, desc="清洗论文"):
        # 读取原始 JSON
        with open(json_path, "r", encoding="utf-8") as f:
            paper_json = json.load(f)

        paper_name = os.path.basename(json_path).replace("_cleaned.json", "")

        # 记录原始大小
        original_chars = len(json.dumps(paper_json))
        total_original_chars += original_chars

        # 执行清洗
        cleaned_text = cleaner.clean_paper(paper_json)
        cleaned_chars = len(cleaned_text)
        total_cleaned_chars += cleaned_chars

        # 保存清洗后的文本
        output_path = os.path.join(OUTPUT_DIR, f"{paper_name}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        # 打印统计
        ratio = (cleaned_chars / original_chars * 100) if original_chars > 0 else 0
        print(
            f"  {paper_name}: {original_chars:,} → {cleaned_chars:,} chars ({ratio:.1f}%)"
        )

    # 最终统计
    print("=" * 60)
    print(f"处理完成: {len(json_files)} 篇论文")
    print(f"原始总字符数: {total_original_chars:,}")
    print(f"清洗后总字符数: {total_cleaned_chars:,}")
    print(f"压缩比: {total_cleaned_chars / total_original_chars * 100:.1f}%")
    print(f"输出目录: {OUTPUT_DIR}")
