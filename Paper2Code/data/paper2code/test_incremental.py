import os
import sys
import json
import glob

# 设置 API key (OpenRouter)
# ⚠️ 请设置环境变量或从配置文件读取
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"
if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("请设置 OPENAI_API_KEY 环境变量")

# 设置 UTF-8 编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from distill_code_repository import GitExtractor, CostEstimator, DistillationEngine


def build_paper_data_list(json_path: str, txt_folder: str):
    with open(json_path, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    repo_url_map = {}
    for conference_papers in dataset_info.values():
        for paper_data in conference_papers:
            repo_name = paper_data.get("repo_name")
            repo_url = paper_data.get("repo_url")
            if repo_name and repo_url:
                repo_url_map[repo_name] = repo_url

    paper_data_list = []
    for filepath in glob.glob(f"{txt_folder}/*.txt"):
        filename = os.path.basename(filepath)
        repo_name = filename.replace(".txt", "")
        repo_url = repo_url_map.get(repo_name)

        if not repo_url:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            cleaned_text = f.read()

        paper_data_list.append(
            {"cleaned_paper_text": cleaned_text, "github_url": repo_url}
        )

    return paper_data_list


def load_existing_dataset(output_file: str) -> list:
    """增量写入：加载已存在的数据集"""
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        print(f"Found existing dataset with {len(existing_data)} records")
        return existing_data
    return []


def save_dataset_incremental(alpaca_dataset: list, output_file: str):
    """增量保存：每条数据处理完立即写入文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(alpaca_dataset, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    OUTPUT_FILE = "train_dataset.json"

    # 测试增量写入
    print("=== 测试增量写入功能 ===")

    # 加载已有数据（如果有）
    alpaca_dataset = load_existing_dataset(OUTPUT_FILE)
    start_count = len(alpaca_dataset)
    print(f"起点: {start_count} 条数据")

    paper_data_list = build_paper_data_list("dataset_info.json", "cleaned_output")

    # 记录已处理的
    processed = set(item.get("github_url", "") for item in alpaca_dataset)

    # 只处理前2个未处理的
    remaining = [
        item for item in paper_data_list if item["github_url"] not in processed
    ][:2]
    print(f"将处理: {len(remaining)} 个新仓库")

    estimator = CostEstimator("gpt-4o")
    distiller = DistillationEngine(
        prompt_file_path="distill_code_repository_system_prompt.md"
    )

    for i, item in enumerate(remaining):
        repo_url = item["github_url"]
        paper_text = item["cleaned_paper_text"]

        print(f"\n[{i + 1}] 处理: {repo_url}")

        # 提取代码
        raw_code = GitExtractor.extract_python_code(repo_url)
        token_count = estimator.count_tokens(raw_code)
        print(f"    Tokens: {token_count}")

        if token_count > 120000:
            print(f"    跳过 (too many tokens)")
            continue

        # 蒸馏
        distilled_golden_code = distiller.distill_code(raw_code)

        # 组装数据
        alpaca_item = {
            "instruction": "You are an expert AI researcher. Implement the core PyTorch model architecture based on the following paper excerpts. Output the code using <file> tags.",
            "input": paper_text,
            "output": distilled_golden_code,
            "github_url": repo_url,
        }
        alpaca_dataset.append(alpaca_item)

        # 增量保存：每条数据处理完立即写入
        save_dataset_incremental(alpaca_dataset, OUTPUT_FILE)
        print(f"    ✅ 已保存！当前: {len(alpaca_dataset)} 条")

        # 验证文件
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            verify = json.load(f)
        print(f"    📁 文件验证: {len(verify)} 条")

    print(f"\n=== 测试完成 ===")
    print(f"新增: {len(alpaca_dataset) - start_count} 条")
    print(f"总计: {len(alpaca_dataset)} 条")
    print(f"文件: {OUTPUT_FILE}")
