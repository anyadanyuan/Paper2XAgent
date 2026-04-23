"""
validate_xkg.py — Stage 3 of paper2XAgent pipeline

对 build_xkg.py 生成的 xKG JSON 执行沙盒验证 + 自调试循环 + 剪枝，
确保所有 Code Node 100% 可执行（xKG 论文 Section 2.2.2 Step 3）。

自调试数据（来自论文 Table 5）：
  - 初始可执行率: ~52.38%
  - 自调试后: 100%
  - 平均 Code Modularization API 调用: 33.36 次（含多轮调试）

Usage:
  python pipeline/validate_xkg.py \\
      --xkg_path outputs/xkg/AttentionCalibration.json \\
      --output_dir outputs/xkg/  # 覆盖写回原文件
      --max_rounds 3             # 每个节点最多调试轮数
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

# 复用 build_xkg 中的工具函数
sys.path.insert(0, str(Path(__file__).parent))
from build_xkg import build_client, llm_call, extract_python_block, extract_last_code_block

_DEBUG_SYSTEM = (
    "You are an expert Python debugging engineer. "
    "You fix runtime errors in AI/ML code while strictly preserving the original algorithm logic."
)

# Prompt: 给定代码 + stderr，输出修复后的完整代码
_DEBUG_PROMPT = """\
You are given a Python code block that failed to execute, along with the error traceback.
Your task is to fix the code so it runs successfully.

# Technique being implemented
{technique_name}: {technique_description}

# Failed Code
```python
{code}
```

# Error Traceback
```
{stderr}
```

# Rules
1. Fix ONLY the error. Do NOT change the core algorithm logic.
2. Common fixes:
   - Add missing imports
   - Fix undefined variable names (create minimal stubs if needed)
   - Fix syntax errors
   - Adjust the # TEST BLOCK to use valid synthetic inputs
   - Replace unavailable external resources with toy data
3. If a package is missing (ModuleNotFoundError), add a `pip install` command at the very top
   of the script using: `import subprocess; subprocess.run([sys.executable, "-m", "pip", "install", "pkg"])`
4. The # TEST BLOCK must run with NO additional setup (no external files, no GPU required).

Return the complete fixed Python script wrapped between two ```:
```python
[... full fixed code ...]
```
"""


# =============================================================================
# 沙盒执行
# =============================================================================

def run_in_sandbox(code: str, timeout: int = 60) -> tuple[int, str, str]:
    """
    在隔离子进程中执行 Python 代码。
    返回 (exit_code, stdout, stderr)。
    超时视为失败。
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TimeoutExpired after {timeout}s"
    except Exception as e:
        return -1, "", str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def extract_test_block(code: str) -> str:
    """
    提取 # TEST BLOCK 之后的部分作为可执行代码。
    若不存在，返回整段代码（让 sandox 执行全部）。
    """
    marker = "# TEST BLOCK"
    idx = code.find(marker)
    if idx == -1:
        return code
    # 找到 TEST BLOCK 所在的 if __name__ == "__main__": 块
    # 直接返回完整代码（包含 TEST BLOCK），让 Python 解释器判断是否在 __main__
    return code


def make_runnable(code: str) -> str:
    """
    确保代码中的 TEST BLOCK 在直接运行时会被执行。
    如果 TEST BLOCK 在 if __name__ == '__main__': 下，直接调用没问题。
    如果没有 if __name__ 保护，也没问题。
    """
    return code


# =============================================================================
# 自调试循环
# =============================================================================

def debug_one(
    client: OpenAI,
    model: str,
    technique_name: str,
    technique_description: str,
    code: str,
    max_rounds: int = 3,
    timeout: int = 60,
) -> tuple[Optional[str], bool, int]:
    """
    对单个 Code Node 执行自调试循环。

    Returns:
        (final_code, is_executable, rounds_used)
        final_code 为 None 表示穷尽重试后仍失败（触发剪枝）。
    """
    current_code = code

    for round_idx in range(max_rounds + 1):  # round 0 = 首次执行（不需要修复）
        exit_code, stdout, stderr = run_in_sandbox(
            make_runnable(current_code), timeout=timeout
        )

        if exit_code == 0:
            print(f"    ✓ Executable (round={round_idx})")
            return current_code, True, round_idx

        if round_idx == max_rounds:
            print(f"    ✗ Still failing after {max_rounds} debug rounds → PRUNE")
            return None, False, round_idx

        # 调试
        print(f"    Round {round_idx + 1}/{max_rounds} — error: {stderr[:120].strip()}")
        prompt = _DEBUG_PROMPT.format(
            technique_name=technique_name,
            technique_description=technique_description[:400],
            code=current_code[:8000],
            stderr=stderr[:3000],
        )
        raw = llm_call(client, model, _DEBUG_SYSTEM, prompt, temperature=0.2)
        fixed = extract_python_block(raw)
        if not fixed:
            print(f"    LLM returned no code block in debug round {round_idx + 1}")
            continue
        current_code = fixed

    return None, False, max_rounds


# =============================================================================
# 递归处理 xKG 节点树
# =============================================================================

def validate_node(
    client: OpenAI,
    model: str,
    node: dict,
    max_rounds: int,
    timeout: int,
    stats: dict,
) -> Optional[dict]:
    """
    递归验证节点及其子节点。
    返回验证/修复后的节点，或 None（剪枝）。
    """
    tech_name = node.get("name", "Unknown")
    tech_desc = node.get("description", "")

    # 先递归处理子节点
    raw_subs = node.get("components", [])
    valid_subs: list[dict] = []
    for sub in raw_subs:
        result = validate_node(client, model, sub, max_rounds, timeout, stats)
        if result is not None:
            valid_subs.append(result)

    # 验证当前节点
    code_node = node.get("code")
    if not code_node:
        # Finding/Resource 等无代码节点，直接保留
        node["components"] = valid_subs
        return node

    implementation = code_node.get("implementation", "")
    if not implementation.strip():
        print(f"  [PRUNE] {tech_name}: empty implementation")
        stats["pruned"] += 1
        return None

    print(f"  [Validate] {tech_name}")
    stats["total"] += 1

    final_code, ok, rounds = debug_one(
        client, model, tech_name, tech_desc,
        implementation, max_rounds=max_rounds, timeout=timeout,
    )

    if not ok:
        stats["pruned"] += 1
        return None  # Knowledge Filtering: 剪枝

    stats["passed"] += 1
    if rounds > 0:
        stats["debugged"] += 1

    # 更新节点
    result = dict(node)
    result["code"] = dict(code_node)
    result["code"]["implementation"] = final_code
    result["verified"] = True
    result["components"] = valid_subs
    return result


# =============================================================================
# 主流程
# =============================================================================

def validate_xkg(
    xkg: dict,
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_rounds: int = 3,
    timeout: int = 60,
) -> dict:
    """
    对整个 xKG 执行沙盒验证 + 自调试 + Knowledge Filtering。
    返回更新后的 xKG（所有保留节点均可执行）。
    """
    print(f"\n{'='*60}")
    print(f"Validating xKG: {xkg.get('paper_title', '?')}")
    print(f"  max_rounds={max_rounds}, timeout={timeout}s")
    print(f"{'='*60}\n")

    stats = {"total": 0, "passed": 0, "pruned": 0, "debugged": 0}

    valid_techniques: list[dict] = []
    for tech in xkg.get("techniques", []):
        result = validate_node(client, model, tech, max_rounds, timeout, stats)
        if result is not None:
            valid_techniques.append(result)

    print(f"\n{'='*60}")
    print(f"Validation complete for: {xkg.get('paper_title', '?')}")
    print(f"  Total code nodes : {stats['total']}")
    print(f"  Passed           : {stats['passed']} ({100*stats['passed']//max(stats['total'],1)}%)")
    print(f"  Self-debugged    : {stats['debugged']}")
    print(f"  Pruned           : {stats['pruned']}")
    print(f"{'='*60}\n")

    result_xkg = dict(xkg)
    result_xkg["techniques"] = valid_techniques
    result_xkg["validation_stats"] = stats
    return result_xkg


# =============================================================================
# CLI 入口
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate xKG code nodes: sandbox execution + self-debug + pruning"
    )
    parser.add_argument("--xkg_path", required=True,
                        help="Path to xKG JSON (output of build_xkg.py)")
    parser.add_argument("--output_dir", default=None,
                        help="Output directory (default: same as input)")
    parser.add_argument("--model", default="gpt-4.1-mini",
                        help="LLM for self-debugging")
    parser.add_argument("--max_rounds", type=int, default=3,
                        help="Max self-debug rounds per node (default: 3)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Sandbox execution timeout in seconds (default: 60)")
    parser.add_argument("--api_key", default=None,
                        help="OpenAI/OpenRouter API key")
    args = parser.parse_args()

    xkg_path = Path(args.xkg_path)
    xkg = json.loads(xkg_path.read_text(encoding="utf-8"))

    client = build_client(args.api_key)

    validated_xkg = validate_xkg(
        xkg=xkg,
        client=client,
        model=args.model,
        max_rounds=args.max_rounds,
        timeout=args.timeout,
    )

    # 保存（默认覆盖原文件，加 _validated 后缀便于区分）
    out_dir = Path(args.output_dir) if args.output_dir else xkg_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_name = xkg.get("paper_title", xkg_path.stem)
    out_path = out_dir / f"{paper_name}_validated.json"
    out_path.write_text(
        json.dumps(validated_xkg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Validated xKG saved to: {out_path}")


if __name__ == "__main__":
    main()
