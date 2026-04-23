"""
test_evaluators.py - 评测器功能测试

快速验证各个评测器的基本功能。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.sandbox import run_in_sandbox, check_syntax
from utils.code_parser import extract_code
from evaluators.execution_eval import ExecutionEvaluator
from evaluators.fidelity_eval import FidelityEvaluator


def test_sandbox():
    """测试沙盒执行"""
    print("\n[Test] Sandbox Execution")
    print("-" * 60)

    # 测试成功执行
    code_success = """
import torch
print("Hello from sandbox!")
x = torch.tensor([1, 2, 3])
print(f"Tensor: {x}")
"""

    exit_code, stdout, stderr = run_in_sandbox(code_success, timeout=5)
    print(f"✅ Success case: exit_code={exit_code}")
    print(f"   stdout: {stdout.strip()}")

    # 测试失败执行
    code_fail = """
import nonexistent_module
"""

    exit_code, stdout, stderr = run_in_sandbox(code_fail, timeout=5)
    print(f"✅ Failure case: exit_code={exit_code}")
    print(f"   stderr: {stderr[:100]}...")


def test_code_parser():
    """测试代码提取"""
    print("\n[Test] Code Parser")
    print("-" * 60)

    # 测试 XML 格式
    xml_output = """
<file name="model.py">
import torch
import torch.nn as nn

class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
    
    def forward(self, x):
        return x
</file>
"""

    code = extract_code(xml_output)
    print(f"✅ XML extraction: {len(code)} chars")
    print(f"   Preview: {code[:50]}...")

    # 测试 Markdown 格式
    md_output = """
Here is the model implementation:

```python
import torch
class SimpleModel:
    pass
```
"""

    code = extract_code(md_output)
    print(f"✅ Markdown extraction: {len(code)} chars")
    print(f"   Preview: {code[:50]}...")


def test_execution_eval():
    """测试可运行性评估"""
    print("\n[Test] Execution Evaluator")
    print("-" * 60)

    evaluator = ExecutionEvaluator(timeout=5)

    # 测试可运行代码
    code = """
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(10, 5)
    
    def forward(self, x):
        return self.linear(x)

# 简单测试
model = Model()
x = torch.randn(2, 10)
y = model(x)
print(f"Output shape: {y.shape}")
"""

    result = evaluator.evaluate(code)
    print(f"✅ Evaluation result:")
    print(f"   XPR: {result['xpr']}")
    print(f"   SAR: {result['sar']}")
    print(f"   SYR: {result['syr']}")
    print(f"   Exec time: {result['exec_time']:.2f}s")


def test_fidelity_eval():
    """测试忠实度评估"""
    print("\n[Test] Fidelity Evaluator")
    print("-" * 60)

    evaluator = FidelityEvaluator()

    pred_code = """
import torch
import torch.nn as nn

class TransformerBlock(nn.Module):
    def __init__(self, d_model=512, nhead=8):
        super().__init__()
        self.attention = nn.MultiheadAttention(d_model, nhead)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ffn = nn.Linear(d_model, d_model * 4)
    
    def forward(self, x):
        # Residual connection
        attn_out, _ = self.attention(x, x, x)
        x = x + self.norm1(attn_out)
        
        # FFN with residual
        ffn_out = self.ffn(x)
        x = x + self.norm2(ffn_out)
        return x
"""

    ref_code = """
import torch
import torch.nn as nn

class AttentionLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.mha = nn.MultiheadAttention(512, 8)
        self.layer_norm = nn.LayerNorm(512)
    
    def forward(self, x):
        out, _ = self.mha(x, x, x)
        return self.layer_norm(out + x)
"""

    paper_text = """
The Transformer uses multi-head attention and layer normalization.
Each layer applies attention followed by a feed-forward network,
with residual connections around each sub-layer.
"""

    # 注意：这里不会真正调用 LLM（没有 API key）
    result = evaluator.evaluate(
        pred_code=pred_code,
        paper_text=paper_text,
        paper_id="test_001",
        ref_code=ref_code,
    )

    print(f"✅ Fidelity evaluation:")
    print(f"   PCR: {result['pcr']:.2%}")
    print(f"   AAR: {result['aar']:.2%}")
    print(f"   CodeBERTScore: {result['codebertscore']:.3f}")
    print(f"   Component hits: {result['component_hits'][:3]}...")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Evaluation System - Functional Tests")
    print("=" * 60)

    try:
        test_sandbox()
    except Exception as e:
        print(f"❌ Sandbox test failed: {e}")

    try:
        test_code_parser()
    except Exception as e:
        print(f"❌ Code parser test failed: {e}")

    try:
        test_execution_eval()
    except Exception as e:
        print(f"❌ Execution eval test failed: {e}")

    try:
        test_fidelity_eval()
    except Exception as e:
        print(f"❌ Fidelity eval test failed: {e}")

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
