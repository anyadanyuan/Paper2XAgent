import os
import sys
import json
import glob
from typing import List, Dict

# 设置 API key (OpenRouter)
# ⚠️ 请设置环境变量或从配置文件读取
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

# 设置 UTF-8 编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# import distill_code_repository
from distill_code_repository import GitExtractor, CostEstimator, DistillationEngine


def build_paper_data_list(json_path: str, txt_folder: str) -> List[Dict[str, str]]:
    """
    合并本地 TXT 论文数据和 JSON 里的远程 Git URL。
    """

    # 使用 json 库将 json_path 文件读取为 Python 字典
    with open(json_path, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    repo_url_map = {}  # 我们的目标是构建类似于 {"auto-j": "https://github.com/...", ...} 的扁平字典
    # dataset_info 的结构是 {"iclr2024": [...], "nips2024": [...]}
    # 所以我们需要遍历它的 values (那些列表)
    for conference_papers in dataset_info.values():
        for paper_data in conference_papers:
            repo_name = paper_data.get("repo_name")
            repo_url = paper_data.get("repo_url")

            if repo_name and repo_url:
                repo_url_map[repo_name] = repo_url

    print(f"✅ 成功构建 Hash Map，内存中包含 {len(repo_url_map)} 个仓库链接。")

    paper_data_list = []

    # 获取 txt_folder 目录下的所有文件列表

    for filepath in glob.glob(f"{txt_folder}/*.txt"):
        filename = os.path.basename(filepath)  # 只需这一行获取纯文件名
        repo_name = filename.replace(".txt", "")
        repo_url = repo_url_map.get(repo_name)

        # 防御性编程：如果因为某种原因匹配不上，优雅地跳过并报警，绝不让程序崩溃
        if not repo_url:
            print(f"⚠️ 警告：文件 {filename} 在 JSON 中找不到对应的 URL，已跳过。")
            continue

        # 读取清洗好的纯文本论文
        txt_path = os.path.join(txt_folder, filename)
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                cleaned_text = f.read()

            # 组装成大模型 ETL 流水线所需的数据格式
            paper_data_list.append(
                {"cleaned_paper_text": cleaned_text, "github_url": repo_url}
            )
        except Exception as e:
            print(f"❌ 读取文件 {txt_path} 失败: {e}")

    print(
        f"🔗 数据合并完毕！共组装了 {len(paper_data_list)} 条有效数据，准备进入蒸馏流水线。"
    )
    return paper_data_list


def load_existing_dataset(output_file: str) -> tuple:
    """增量写入：加载已存在的数据集和已处理仓库列表"""
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        # 从数据中提取已处理的仓库 URL
        processed_urls = set()
        for item in existing_data:
            if "github_url" in item:
                processed_urls.add(item["github_url"])
        print(
            f"📂 发现已有数据集，包含 {len(existing_data)} 条记录, {len(processed_urls)} 个唯一仓库"
        )
        return existing_data, processed_urls
    return [], set()


def save_dataset_incremental(alpaca_dataset: list, output_file: str):
    """增量保存：将数据写入文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(alpaca_dataset, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import logging

    OUTPUT_FILE = "train_dataset.json"

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        filename="generation.log",
        encoding="utf-8",
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(console_handler)

    logging.info("Starting dataset generation...")

    # 增量加载：检查是否已有数据集
    alpaca_dataset, processed_urls = load_existing_dataset(OUTPUT_FILE)

    # 记录当前数量
    start_count = len(alpaca_dataset)
    print(f"📊 当前已有 {start_count} 条数据，将继续处理...")

    paper_data_list = build_paper_data_list(
        json_path="dataset_info.json", txt_folder="cleaned_output"
    )

    # 过滤掉已处理的仓库
    remaining_papers = [
        item for item in paper_data_list if item["github_url"] not in processed_urls
    ]
    print(f"🔄 待处理仓库数: {len(remaining_papers)} / {len(paper_data_list)}")

    estimator = CostEstimator("gpt-4o")
    total_estimated_cost = 0.0
    distiller = DistillationEngine(
        prompt_file_path="distill_code_repository_system_prompt.md"
    )

    # 处理每个仓库
    for idx, item in enumerate(remaining_papers):
        repo_url = item["github_url"]
        paper_text = item["cleaned_paper_text"]

        print(f"[{idx + 1}/{len(remaining_papers)}] 处理: {repo_url}")

        try:
            # 提取 Git 仓库纯文本代码
            raw_code = GitExtractor.extract_python_code(repo_url)

            # Token 与成本拦截防爆
            token_count = estimator.count_tokens(raw_code)
            if token_count > 120000:
                print(f"  🚫 Token 超限 ({token_count})，跳过！")
                continue

            print(f"  🚀 开始蒸馏 | Input Tokens: {token_count}")

            # 提取金标准代码
            distilled_golden_code = distiller.distill_code(raw_code)

            # 组装单条 Alpaca 数据
            alpaca_item = {
                "instruction": "You are an expert AI researcher. Implement the core PyTorch model architecture based on the following paper excerpts. Output the code using <file> tags.",
                "input": paper_text,
                "output": distilled_golden_code,
                "github_url": repo_url,  # 记录仓库 URL 方便去重
            }
            alpaca_dataset.append(alpaca_item)

            # 增量保存：每处理完一条就写入文件
            save_dataset_incremental(alpaca_dataset, OUTPUT_FILE)
            print(f"  ✅ 已保存！当前共 {len(alpaca_dataset)} 条")

        except Exception as e:
            print(f"  ❌ 错误: {e}")
            continue

    print(
        f"\n🎉 完成！共生成 {len(alpaca_dataset) - start_count} 条新数据，总计 {len(alpaca_dataset)} 条"
    )
    print(f"📁 数据已保存至: {OUTPUT_FILE}")
