import json
import sys

def remove_github_url(input_file, output_file=None):
    """
    读取 JSON 文件，移除列表中每个字典的 'github_url' 键，
    并将结果写入输出文件。
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：文件 {input_file} 不存在。")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误：文件 {input_file} 不是有效的 JSON 格式。")
        sys.exit(1)

    # 确保 data 是列表（根据用户描述）
    if not isinstance(data, list):
        print("警告：JSON 数据不是列表，将按原样处理，但可能不是预期格式。")
        # 如果 data 是字典或其他结构，直接删除 github_url
        if isinstance(data, dict) and 'github_url' in data:
            del data['github_url']
    else:
        # 处理列表中的每个元素
        for item in data:
            if isinstance(item, dict) and 'github_url' in item:
                del item['github_url']

    # 确定输出文件名
    if output_file is None:
        # 自动生成新文件名：在原文件名后加 _cleaned
        if input_file.endswith('.json'):
            output_file = input_file.replace('.json', '_cleaned.json')
        else:
            output_file = input_file + '_cleaned'

    # 写回文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"处理完成！结果已保存至：{output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python remove_github_url.py <输入文件> [输出文件]")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    remove_github_url(input_file, output_file)