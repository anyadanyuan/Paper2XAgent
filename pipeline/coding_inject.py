"""
coding_inject.py — Stage 4 全流程编排器（paper2XAgent pipeline）

串联 Paper2Code Stage 4 各子步骤，并在 Stage 4-B (3_coding.py) 注入 xKG 核心代码：

  4-A1  1_planning.py        → {output_dir}/planning_trajectories.json
                               {output_dir}/planning_config.yaml（由 1.1 提取）
  4-A2  1.1_extract_config.py → {output_dir}/planning_config.yaml
        config.yaml 复制       → {output_repo_dir}/config.yaml
  4-A3  2_analyzing.py        → {output_dir}/{file}_simple_analysis_response.json
  4-B   3_coding.py           → {output_repo_dir}/*.py（含 xKG 注入）

Notes:
  - 所有 Paper2Code 脚本以 Paper2Code/codes/ 为工作目录执行（utils 相对导入需要）
  - --skip_planning / --skip_analyzing 支持增量重跑（跳过已完成阶段）
  - 4_debugging.py (Stage 4-C) 有已知 bug (output_repo_dir 参数缺失)，不在此编排

Usage:
  python pipeline/coding_inject.py \\
      --paper_name    AttentionCalibration \\
      --pdf_json_path Paper2Code/data/paper2code/cleaned_output/AttentionCalibration.json \\
      --xkg_path      outputs/xkg/AttentionCalibration_validated.json \\
      --output_dir    outputs/repos/AttentionCalibration \\
      --output_repo_dir outputs/repos/AttentionCalibration/repo \\
      --model         gpt-4.1-mini
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paper2Code 脚本所在目录（subprocess 的 cwd）
_PAPER2CODE_CODES = Path(__file__).parent.parent / "Paper2Code" / "codes"


def _run(cmd: list[str], cwd: Path, step: str) -> None:
    """执行子进程，失败时打印错误并退出。"""
    print(f"\n{'='*60}")
    print(f"[{step}] {' '.join(cmd)}")
    print(f"  cwd: {cwd}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        print(f"[ERROR] {step} failed (exit code {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)


def stage4a_planning(
    paper_name: str,
    pdf_json_path: str,
    output_dir: str,
    output_repo_dir: str,
    model: str,
) -> None:
    """Stage 4-A：规划 + 配置提取"""
    abs_pdf = str(Path(pdf_json_path).resolve())
    abs_out = str(Path(output_dir).resolve())
    abs_repo = str(Path(output_repo_dir).resolve())
    Path(abs_out).mkdir(parents=True, exist_ok=True)
    Path(abs_repo).mkdir(parents=True, exist_ok=True)

    # Step 1: 总体规划
    _run(
        [sys.executable, "1_planning.py",
         "--paper_name", paper_name,
         "--gpt_version", model,
         "--pdf_json_path", abs_pdf,
         "--output_dir", abs_out],
        cwd=_PAPER2CODE_CODES,
        step="4-A1 Planning",
    )

    # Step 2: 提取 config.yaml
    _run(
        [sys.executable, "1.1_extract_config.py",
         "--paper_name", paper_name,
         "--output_dir", abs_out],
        cwd=_PAPER2CODE_CODES,
        step="4-A2 Extract config",
    )

    # Step 3: 把 planning_config.yaml 复制到 repo 目录作为 config.yaml
    src = Path(abs_out) / "planning_config.yaml"
    dst = Path(abs_repo) / "config.yaml"
    shutil.copy2(str(src), str(dst))
    print(f"  ✓ Copied {src} → {dst}")


def stage4a_analyzing(
    paper_name: str,
    pdf_json_path: str,
    output_dir: str,
    model: str,
) -> None:
    """Stage 4-A3：逐文件逻辑分析"""
    abs_pdf = str(Path(pdf_json_path).resolve())
    abs_out = str(Path(output_dir).resolve())

    _run(
        [sys.executable, "2_analyzing.py",
         "--paper_name", paper_name,
         "--gpt_version", model,
         "--pdf_json_path", abs_pdf,
         "--output_dir", abs_out],
        cwd=_PAPER2CODE_CODES,
        step="4-A3 Analyzing",
    )


def stage4b_coding(
    paper_name: str,
    pdf_json_path: str,
    output_dir: str,
    output_repo_dir: str,
    model: str,
    xkg_path: str | None,
) -> None:
    """Stage 4-B：代码生成（含 xKG 注入）"""
    abs_pdf = str(Path(pdf_json_path).resolve())
    abs_out = str(Path(output_dir).resolve())
    abs_repo = str(Path(output_repo_dir).resolve())

    cmd = [
        sys.executable, "3_coding.py",
        "--paper_name", paper_name,
        "--gpt_version", model,
        "--pdf_json_path", abs_pdf,
        "--output_dir", abs_out,
        "--output_repo_dir", abs_repo,
    ]
    if xkg_path:
        cmd += ["--xkg_path", str(Path(xkg_path).resolve())]

    _run(cmd, cwd=_PAPER2CODE_CODES, step="4-B Coding (xKG inject)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 4 orchestrator: planning → analyzing → coding (with xKG injection)"
    )
    parser.add_argument("--paper_name", required=True,
                        help="Paper identifier (e.g. AttentionCalibration)")
    parser.add_argument("--pdf_json_path", required=True,
                        help="Cleaned paper JSON (output of data_cleaner.py)")
    parser.add_argument("--output_dir", required=True,
                        help="Staging dir for planning artifacts and analysis JSONs")
    parser.add_argument("--output_repo_dir", required=True,
                        help="Output directory for the generated code repository")
    parser.add_argument("--model", default="gpt-4.1-mini",
                        help="LLM model (default: gpt-4.1-mini)")
    parser.add_argument("--xkg_path", default=None,
                        help="Validated xKG JSON (output of validate_xkg.py). "
                             "If omitted, runs coding without xKG injection.")
    parser.add_argument("--skip_planning", action="store_true",
                        help="Skip Stage 4-A1/A2 (planning + config extract). "
                             "Use when planning_trajectories.json already exists.")
    parser.add_argument("--skip_analyzing", action="store_true",
                        help="Skip Stage 4-A3 (per-file analysis). "
                             "Use when *_simple_analysis_response.json files already exist.")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  paper2XAgent Stage 4: {args.paper_name}")
    print(f"  model        : {args.model}")
    print(f"  xkg_path     : {args.xkg_path or '(none, no injection)'}")
    print(f"  output_dir   : {args.output_dir}")
    print(f"  output_repo  : {args.output_repo_dir}")
    print(f"{'#'*60}\n")

    if not args.skip_planning:
        stage4a_planning(
            paper_name=args.paper_name,
            pdf_json_path=args.pdf_json_path,
            output_dir=args.output_dir,
            output_repo_dir=args.output_repo_dir,
            model=args.model,
        )
    else:
        print("[SKIP] Stage 4-A1/A2 (planning) — using existing artifacts")

    if not args.skip_analyzing:
        stage4a_analyzing(
            paper_name=args.paper_name,
            pdf_json_path=args.pdf_json_path,
            output_dir=args.output_dir,
            model=args.model,
        )
    else:
        print("[SKIP] Stage 4-A3 (analyzing) — using existing artifacts")

    stage4b_coding(
        paper_name=args.paper_name,
        pdf_json_path=args.pdf_json_path,
        output_dir=args.output_dir,
        output_repo_dir=args.output_repo_dir,
        model=args.model,
        xkg_path=args.xkg_path,
    )

    print(f"\n{'#'*60}")
    print(f"  Stage 4 complete: {args.paper_name}")
    print(f"  Generated repo : {args.output_repo_dir}")
    if args.xkg_path:
        print(f"  xKG injected   : {args.xkg_path}")
    print(f"  Next step      : python pipeline/refine_repo.py --repo_dir {args.output_repo_dir}")
    print(f"{'#'*60}\n")


if __name__ == "__main__":
    main()
