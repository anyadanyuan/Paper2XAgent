import os
import json

import os

def hunt_for_corruption(txt_folder: str, json_folder: str):
    """
    数据清洗雷达：精准定位乱码源头
    """
    corrupted_files = []

    # 1. 扫描你的中间产物：cleaned_output 文件夹下的 txt
    print(f"🕵️ 正在扫描 {txt_folder} 寻找污染源...")
    for filename in os.listdir(txt_folder):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(txt_folder, filename)

        # 以二进制模式打开，避免文本编码转换干扰
        with open(filepath, 'rb') as f:
            content_bytes = f.read()
            # U+FFFD 的 UTF-8 编码是三个字节：0xEF 0xBF 0xBD
            if b'\xef\xbf\xbd' in content_bytes:
                corrupted_files.append(filename)

                # 寻找第一个出现位置，并提取上下文（转为字符串便于显示）
                idx = content_bytes.find(b'\xef\xbf\xbd')
                # 取前后各 50 个字节，并尝试用 utf-8 解码显示（忽略错误）
                start = max(0, idx - 50)
                end = min(len(content_bytes), idx + 50)
                context_bytes = content_bytes[start:end]
                # 尝试用 utf-8 解码上下文，可能包含乱码，用 replace 避免报错
                context_str = context_bytes.decode('utf-8', errors='replace')
                print(f"\n🚨 发现污染！文件: {filename}")
                print(f"🔍 案发现场上下文: ...{context_str}...")

    if not corrupted_files:
        print("\n✅ TXT 文件中未发现乱码。去检查最终生成的 Alpaca JSON 文件！")

    # 2. 溯源追踪：去原始 JSON 里对峙
    print("\n===========================================")
    print("🔬 溯源阶段：检查原始 JSON 是否已存在乱码")
    print("===========================================")
    
    for filename in corrupted_files:
        # 假设你的原始 JSON 文件名和 txt 有对应关系，比如 auto-j.txt 对应 auto-j_cleaned.json
        # 请根据你的实际命名规则修改这里的替换逻辑
        original_json_name = filename.replace(".txt", "_cleaned.json") 
        original_json_path = os.path.join(json_folder, original_json_name)
        
        if not os.path.exists(original_json_path):
            print(f"⚠️ 找不到原始文件 {original_json_path}")
            continue
            
        with open(original_json_path, 'rb') as f:
            raw_content = f.read()
            if b'\xef\xbf\xbd' in raw_content:
                print(f"💀 结论：锅是上游的！在原始文件 {original_json_name} 中就已经存在乱码！")
                print("   👉 建议：这是 PDF 解析器的缺陷，如果你使用的预处理数据集本身就有，大模型通常有一定容错率，少量  可直接忽略或正则替换为空格。")
            else:
                print(f"🤡 结论：锅是你的！原始文件 {original_json_name} 中没有乱码。")
                print("   👉 建议：检查你的清洗脚本，在使用 open() 写入 txt 时，是否漏写了 encoding='utf-8'！")

# 运行雷达
# 请填入你存放清洗后 txt 的文件夹路径，和存放原始 json 的文件夹路径
hunt_for_corruption(txt_folder="cleaned_output", json_folder="nips2024")