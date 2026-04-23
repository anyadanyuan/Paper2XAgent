"""
端到端快速测试：用 train_dataset.json 中的第一条数据运行 build_xkg.py。

Usage:
  python pipeline/test_build_xkg.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_PATH = Path(__file__).parent.parent.parent / "Paper2Code/data/paper2code/train_dataset.json"


def load_sample() -> tuple[str, str]:
    """从 train_dataset.json 读取第一条样本"""
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    sample = data[0]
    paper_text: str = sample["input"]    # cleaned paper text
    qwen_output: str = sample["output"]  # <file ...>...</file> XML
    return paper_text, qwen_output


def test_qwen_output_provider():
    from build_xkg import QwenOutputProvider
    _, qwen_xml = load_sample()
    provider = QwenOutputProvider(qwen_xml)
    file_dict = provider.provide("TestPaper", "")
    print(f"[test_qwen_output_provider] Parsed {len(file_dict)} files: {list(file_dict.keys())}")
    assert len(file_dict) > 0, "Should parse at least one file"
    print("  PASSED")


def test_extract_abstract():
    from build_xkg import _extract_abstract
    paper_text, _ = load_sample()
    abstract = _extract_abstract(paper_text)
    print(f"[test_extract_abstract] Abstract ({len(abstract)} chars): {abstract[:100]}...")
    assert len(abstract) > 50
    print("  PASSED")


def test_make_code_node():
    from build_xkg import make_code_node
    code = "import torch\nimport numpy as np\n\nclass MyModel(torch.nn.Module):\n    pass\n"
    node = make_code_node(code)
    assert "implementation" in node
    assert "documentation" in node
    assert "package" in node
    assert "torch" in node["package"]
    assert "numpy" in node["package"]  # import numpy as np → top-level name "numpy" extracted
    print(f"[test_make_code_node] packages: {node['package']}")
    print("  PASSED")


def test_make_technique_node():
    from build_xkg import make_technique_node, make_code_node
    code = make_code_node("import torch\n")
    node = make_technique_node(
        name="Test Technique",
        description="A test",
        code=code,
        tech_type="Methodology",
        verified=None,
    )
    assert node["name"] == "Test Technique"
    assert "verified" not in node  # verified=None → field omitted
    print(f"[test_make_technique_node] node keys: {list(node.keys())}")
    print("  PASSED")


def test_full_pipeline():
    """完整流程：QwenOutputProvider → build_xkg → 验证结构"""
    from build_xkg import QwenOutputProvider, build_xkg

    paper_text, qwen_xml = load_sample()
    provider = QwenOutputProvider(qwen_xml)
    xkg = build_xkg(
        paper_title="TestPaper",
        paper_text=paper_text,
        provider=provider,
    )

    assert "paper_title" in xkg
    assert "abstract" in xkg
    assert "techniques" in xkg
    assert len(xkg["techniques"]) > 0, "Should have at least one technique node"

    node = xkg["techniques"][0]
    assert "name" in node
    assert "code" in node
    assert "implementation" in node["code"]
    assert "verified" not in node  # pending validate_xkg.py

    print(f"[test_full_pipeline] xKG: {len(xkg['techniques'])} node(s)")
    for n in xkg["techniques"]:
        pkgs = n["code"]["package"]
        print(f"  - {n['name']} | packages: {pkgs}")
    print("  PASSED")


if __name__ == "__main__":
    print(f"{'='*60}")
    print("Running build_xkg tests")
    print(f"{'='*60}\n")

    test_qwen_output_provider()
    test_extract_abstract()
    test_make_code_node()
    test_make_technique_node()
    test_full_pipeline()

    print(f"\n{'='*60}")
    print("All tests passed!")
    print(f"{'='*60}")
