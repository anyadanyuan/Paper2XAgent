"""
refine_repo.py — Stage 5 of paper2XAgent pipeline

使用 aider Repo Map 分析跨文件符号依赖，批量修复：
  - import 错误（未定义名称、错误模块路径）
  - 接口不一致（方法签名不匹配、参数名错误）
  - 类/函数引用但未定义的占位问题

aider 会生成 Repo Map（用语言解析器分析所有 .py 文件的 symbol tree），
让 LLM 在一次上下文中看到全仓库的符号关系，从而做跨文件一致性修复。

Usage:
  python pipeline/refine_repo.py \\
      --repo_dir  outputs/repos/AttentionCalibration/repo \\
      --model     gpt-4.1-mini \\
      --rounds    2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ── aider 源码路径（本地 clone）──────────────────────────────────────────────
_AIDER_ROOT = Path(__file__).parent.parent / "aider"
if str(_AIDER_ROOT) not in sys.path:
    sys.path.insert(0, str(_AIDER_ROOT))


_FIX_PROMPT = """\
You are a Python expert performing a cross-file consistency review on a \
machine-generated research code repository.

Your tasks — fix ALL of the following issues you find:
1. **Import errors**: undefined names, wrong module paths, missing `__init__.py` imports.
2. **Interface mismatches**: a function/method is called with arguments that don't \
match its definition (wrong names, wrong count, wrong types).
3. **Missing stubs**: a class or function is referenced but never defined; add a \
minimal correct implementation.
4. **Circular imports**: restructure imports to break cycles.
5. **Config key errors**: keys read from config.yaml that don't exist in the file.

Rules:
- Fix ONLY what is broken. Do NOT restructure, rename, or reformat working code.
- Keep the original algorithm logic strictly intact.
- If a fix requires adding a new import, add it at the top of the file.
- After fixing, every file must be importable with `python -c "import <module>"`.
"""


def collect_py_files(repo_dir: Path) -> list[str]:
    """递归收集 repo_dir 下所有 .py 文件的绝对路径。"""
    files = []
    for p in sorted(repo_dir.rglob("*.py")):
        if any(part.startswith(".") for part in p.parts):
            continue
        files.append(str(p))
    return files


def run_refine(repo_dir: Path, model_name: str, rounds: int) -> None:
    from aider.coders import Coder
    from aider.io import InputOutput
    from aider.models import Model

    py_files = collect_py_files(repo_dir)
    if not py_files:
        print(f"[refine_repo] No .py files found in {repo_dir}")
        return

    print(f"\n{'='*60}")
    print(f"[refine_repo] Repo   : {repo_dir}")
    print(f"[refine_repo] Model  : {model_name}")
    print(f"[refine_repo] Files  : {len(py_files)}")
    print(f"[refine_repo] Rounds : {rounds}")
    print(f"{'='*60}\n")

    for round_idx in range(1, rounds + 1):
        print(f"--- Round {round_idx}/{rounds} ---")
        coder = Coder.create(
            main_model=Model(model_name),
            fnames=py_files,
            io=InputOutput(yes=True),
            auto_commits=False,
        )
        coder.run(_FIX_PROMPT)
        print(f"  ✓ Round {round_idx} complete")

    print(f"\n[refine_repo] Done. Repo at: {repo_dir}")
    print(f"Next step: python Paper2Code/codes/eval.py ...")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 5: aider Repo Map cross-file consistency fix"
    )
    parser.add_argument("--repo_dir", required=True,
                        help="Generated code repo directory (output of coding_inject.py)")
    parser.add_argument("--model", default="gpt-4.1-mini",
                        help="LLM model for aider (default: gpt-4.1-mini)")
    parser.add_argument("--rounds", type=int, default=1,
                        help="Number of fix rounds (default: 1)")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    repo_dir = Path(args.repo_dir).resolve()
    if not repo_dir.is_dir():
        print(f"[ERROR] repo_dir not found: {repo_dir}", file=sys.stderr)
        sys.exit(1)

    run_refine(repo_dir=repo_dir, model_name=args.model, rounds=args.rounds)


if __name__ == "__main__":
    main()
