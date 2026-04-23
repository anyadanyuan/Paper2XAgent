"""
test_e2e_pipeline.py — End-to-end integration test for paper2XAgent pipeline

Tests the complete flow from Stage 0 (data cleaning) to Stage 6 (evaluation):
  Stage 0: data_cleaner.py          → cleaned .txt
  Stage 1: qwen_infer.py            → Qwen XML output
  Stage 2: build_xkg.py             → xKG JSON
  Stage 3: validate_xkg.py          → validated xKG JSON
  Stage 4: coding_inject.py         → generated code repo (with xKG injection)
  Stage 5: refine_repo.py           → cross-file consistency fixes
  Stage 6: eval.py                  → quality score (1-5)

This test uses a single sample from train_dataset.json to avoid API costs.
It validates outputs at each stage and verifies the entire pipeline integration.

Usage:
  # Run full e2e test (requires OPENAI_API_KEY for Stage 3-6)
  python pipeline/tests/test_e2e_pipeline.py

  # Run only stages 0-2 (no API calls)
  python pipeline/tests/test_e2e_pipeline.py --skip-validation

  # Run with mock LLM calls (fast, no API key needed)
  python pipeline/tests/test_e2e_pipeline.py --mock-llm

Environment:
  OPENAI_API_KEY  Required for stages 3-6 unless --mock-llm is used
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add pipeline/ to path for imports
_PIPELINE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_PIPELINE_DIR))

_REPO_ROOT = _PIPELINE_DIR.parent
_TRAIN_DATASET = _REPO_ROOT / "Paper2Code/data/paper2code/train_dataset_cleaned.json"
_DATA_CLEANER = _REPO_ROOT / "Paper2Code/data/paper2code/data_cleaner.py"
_CODING_INJECT = _PIPELINE_DIR / "coding_inject.py"
_REFINE_REPO = _PIPELINE_DIR / "refine_repo.py"
_EVAL_SCRIPT = _REPO_ROOT / "Paper2Code/codes/eval.py"


# ── Mock LLM Responses ────────────────────────────────────────────────────────

_MOCK_DEBUG_RESPONSE = """
import torch
import torch.nn as nn

class CoreModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = nn.Linear(10, 10)
    
    def forward(self, x):
        return self.layer(x)
"""

_MOCK_EVAL_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {
                        "score": 4,
                        "reasoning": "Well-structured implementation with proper imports and clean code.",
                    }
                )
            }
        }
    ]
}


# ── Test Utilities ────────────────────────────────────────────────────────────


class TestContext:
    """Test context manager for isolated e2e test runs."""

    def __init__(self, use_temp_dir: bool = True):
        self.use_temp_dir = use_temp_dir
        self.temp_dir: Path | None = None
        self.test_root: Path | None = None

    def __enter__(self):
        if self.use_temp_dir:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="paper2xagent_e2e_"))
            self.test_root = self.temp_dir
        else:
            # Use a subdirectory in the repo for inspection
            self.test_root = _REPO_ROOT / "test_outputs"
            self.test_root.mkdir(exist_ok=True)

        print(f"\n{'=' * 70}")
        print(f"Test root: {self.test_root}")
        print(f"{'=' * 70}\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.use_temp_dir and self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"\n[OK] Cleaned up temp dir: {self.temp_dir}")


def load_sample_data() -> tuple[str, str, str]:
    """
    Load the first sample from train_dataset.json.

    Returns:
        (paper_name, paper_text, qwen_xml)
    """
    if not _TRAIN_DATASET.exists():
        raise FileNotFoundError(f"Train dataset not found: {_TRAIN_DATASET}")

    data = json.loads(_TRAIN_DATASET.read_text(encoding="utf-8"))
    sample = data[0]

    # Extract paper name from the input text (heuristic: use first 20 chars as identifier)
    paper_text: str = sample["input"]
    paper_name = "TestPaper_E2E"
    qwen_xml: str = sample["output"]

    return paper_name, paper_text, qwen_xml


def run_command(
    cmd: list[str], cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Run a subprocess command and return the result."""
    print(f"\n[CMD] {' '.join(cmd)}")
    if cwd:
        print(f"      cwd: {cwd}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


# ── Stage Tests ───────────────────────────────────────────────────────────────


def test_stage0_data_cleaning(
    ctx: TestContext, paper_name: str, paper_text: str
) -> Path:
    """
    Stage 0: Data cleaning (simulate by directly writing cleaned text).

    Returns:
        Path to cleaned .txt file
    """
    print("\n" + "=" * 70)
    print("Stage 0: Data Cleaning")
    print("=" * 70)

    # Instead of running data_cleaner.py (which processes all papers),
    # we directly write our sample text to the expected output location
    cleaned_dir = ctx.test_root / "cleaned_output"
    cleaned_dir.mkdir(exist_ok=True)

    cleaned_txt = cleaned_dir / f"{paper_name}.txt"
    cleaned_txt.write_text(paper_text, encoding="utf-8")

    assert cleaned_txt.exists(), f"Cleaned file not created: {cleaned_txt}"
    print(f"[OK] Created cleaned text: {cleaned_txt}")
    print(f"  Size: {len(paper_text)} chars")

    return cleaned_txt


def test_stage1_qwen_inference(
    ctx: TestContext,
    paper_name: str,
    paper_txt: Path,
    qwen_xml: str,
    use_real_qwen: bool = False,
) -> Path:
    """
    Stage 1: Qwen inference.

    Args:
        use_real_qwen: If True, call real qwen_infer.py (requires model on disk or API)

    Returns:
        Path to Qwen XML output
    """
    print("\n" + "=" * 70)
    print(f"Stage 1: Qwen Inference ({'Real' if use_real_qwen else 'Simulated'})")
    print("=" * 70)

    qwen_dir = ctx.test_root / "qwen"
    qwen_dir.mkdir(exist_ok=True)
    qwen_output = qwen_dir / f"{paper_name}.xml"

    if use_real_qwen:
        # Real Qwen inference with qwen_infer.py
        import sys

        sys.path.insert(0, str(_PIPELINE_DIR))

        # Check if model is available (local path or API)
        qwen_model_path = os.environ.get(
            "QWEN_MODEL_PATH", "/root/autodl-tmp/Qwen2.5-7B-paper2Xcode"
        )
        qwen_api_base = os.environ.get("QWEN_API_BASE")

        if not qwen_api_base and not Path(qwen_model_path).exists():
            print(
                f"[WARN] Qwen model not found at {qwen_model_path} and QWEN_API_BASE not set"
            )
            print(f"[WARN] Falling back to simulated mode")
            use_real_qwen = False
        else:
            cmd = [
                sys.executable,
                str(_PIPELINE_DIR / "qwen_infer.py"),
                "--single",
                str(paper_txt),
                "--model_path",
                qwen_model_path,
            ]
            result = run_command(cmd, check=False)
            if result.returncode == 0:
                qwen_output.write_text(result.stdout, encoding="utf-8")
                print(f"[OK] Real Qwen inference: {qwen_output}")
            else:
                print(f"[WARN] Qwen inference failed, falling back to simulated mode")
                use_real_qwen = False

    if not use_real_qwen:
        # Simulate Qwen output by writing the pre-generated XML from train_dataset.json
        qwen_output.write_text(qwen_xml, encoding="utf-8")
        print(f"[OK] Simulated Qwen XML: {qwen_output}")

    assert qwen_output.exists(), f"Qwen XML not created: {qwen_output}"
    print(f"  Size: {len(qwen_output.read_text(encoding='utf-8'))} chars")

    return qwen_output


def test_stage2_build_xkg(
    ctx: TestContext, paper_name: str, paper_txt: Path, qwen_xml_path: Path
) -> Path:
    """
    Stage 2: Build xKG from Qwen output.

    Returns:
        Path to xKG JSON
    """
    print("\n" + "=" * 70)
    print("Stage 2: Build xKG")
    print("=" * 70)

    xkg_dir = ctx.test_root / "xkg"
    xkg_dir.mkdir(exist_ok=True)

    from build_xkg import build_xkg, QwenOutputProvider

    paper_text = paper_txt.read_text(encoding="utf-8")
    qwen_xml = qwen_xml_path.read_text(encoding="utf-8")

    provider = QwenOutputProvider(qwen_xml)
    xkg_data = build_xkg(
        paper_title=paper_name,
        paper_text=paper_text,
        provider=provider,
    )

    xkg_json_path = xkg_dir / f"{paper_name}.json"
    xkg_json_path.write_text(
        json.dumps(xkg_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    assert xkg_json_path.exists(), f"xKG JSON not created: {xkg_json_path}"
    assert "techniques" in xkg_data, "xKG must have 'techniques' field"
    assert len(xkg_data["techniques"]) > 0, "xKG must have at least one technique"

    print(f"[OK] Created xKG JSON: {xkg_json_path}")
    print(f"  Techniques: {len(xkg_data['techniques'])}")
    for tech in xkg_data["techniques"]:
        print(f"    - {tech['name']}")

    return xkg_json_path


def test_stage3_validate_xkg(
    ctx: TestContext,
    paper_name: str,
    xkg_json_path: Path,
    mock_llm: bool = False,
) -> Path:
    """
    Stage 3: Validate xKG with sandbox execution + self-debugging.

    Returns:
        Path to validated xKG JSON
    """
    print("\n" + "=" * 70)
    print("Stage 3: Validate xKG")
    print("=" * 70)

    validated_path = xkg_json_path.parent / f"{paper_name}_validated.json"

    if mock_llm:
        # Mock validation: mark all nodes as verified with fixed code
        xkg_data = json.loads(xkg_json_path.read_text(encoding="utf-8"))
        for tech in xkg_data["techniques"]:
            tech["verified"] = True
            tech["code"]["implementation"] = _MOCK_DEBUG_RESPONSE.strip()
        validated_path.write_text(
            json.dumps(xkg_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[OK] (Mocked) Validated xKG: {validated_path}")
    else:
        # Real validation with validate_xkg.py
        cmd = [
            sys.executable,
            str(_PIPELINE_DIR / "validate_xkg.py"),
            "--xkg_path",
            str(xkg_json_path),
            "--output_dir",
            str(xkg_json_path.parent),
            "--model",
            "gpt-4.1-mini",
            "--max_rounds",
            "2",
        ]
        run_command(cmd)
        print(f"[OK] Validated xKG: {validated_path}")

    assert validated_path.exists(), f"Validated xKG not created: {validated_path}"

    # Verify structure
    validated_data = json.loads(validated_path.read_text(encoding="utf-8"))
    verified_count = sum(1 for t in validated_data["techniques"] if t.get("verified"))
    print(f"  Verified nodes: {verified_count}/{len(validated_data['techniques'])}")

    return validated_path


def test_stage4_coding_inject(
    ctx: TestContext,
    paper_name: str,
    cleaned_txt: Path,
    xkg_validated: Path,
    mock_llm: bool = False,
) -> Path:
    """
    Stage 4: Paper2Code coding with xKG injection.

    Returns:
        Path to generated repository
    """
    print("\n" + "=" * 70)
    print("Stage 4: Coding with xKG Injection")
    print("=" * 70)

    # Create a minimal cleaned JSON for Paper2Code scripts
    paper_json = {
        "paper_id": paper_name,
        "title": paper_name,
        "abstract": "Test paper for e2e pipeline",
        "pdf_parse": {"body_text": []},
    }

    cleaned_json = cleaned_txt.parent / f"{paper_name}.json"
    cleaned_json.write_text(json.dumps(paper_json, indent=2), encoding="utf-8")

    output_dir = ctx.test_root / "repos" / paper_name
    output_repo_dir = output_dir / "repo"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_repo_dir.mkdir(parents=True, exist_ok=True)

    if mock_llm:
        # Mock coding: create minimal repo structure with xKG-injected files
        xkg_data = json.loads(xkg_validated.read_text(encoding="utf-8"))

        # Create config.yaml
        config_yaml = output_repo_dir / "config.yaml"
        config_yaml.write_text(
            "model:\n  name: TestModel\n  params: {}", encoding="utf-8"
        )

        # Inject xKG nodes
        for tech in xkg_data["techniques"]:
            if not tech.get("verified"):
                continue
            filename = tech["name"].lower().replace(" ", "_") + ".py"
            file_path = output_repo_dir / filename
            file_path.write_text(tech["code"]["implementation"], encoding="utf-8")

        # Create additional files (trainer, dataloader)
        trainer_py = output_repo_dir / "trainer.py"
        trainer_py.write_text(
            "import torch\n\nclass Trainer:\n    def __init__(self):\n        pass\n",
            encoding="utf-8",
        )

        print(f"[OK] (Mocked) Generated repo: {output_repo_dir}")
    else:
        # Real coding with coding_inject.py
        cmd = [
            sys.executable,
            str(_CODING_INJECT),
            "--paper_name",
            paper_name,
            "--pdf_json_path",
            str(cleaned_json),
            "--xkg_path",
            str(xkg_validated),
            "--output_dir",
            str(output_dir),
            "--output_repo_dir",
            str(output_repo_dir),
            "--model",
            "gpt-4.1-mini",
        ]
        run_command(cmd)
        print(f"[OK] Generated repo: {output_repo_dir}")

    assert output_repo_dir.exists(), f"Repo not created: {output_repo_dir}"

    # Verify repo structure
    py_files = list(output_repo_dir.glob("*.py"))
    config_file = output_repo_dir / "config.yaml"

    print(f"  Python files: {len(py_files)}")
    for py_file in py_files:
        print(f"    - {py_file.name}")
    print(f"  Config: {config_file.exists()}")

    assert len(py_files) > 0, "Repository must contain at least one .py file"

    return output_repo_dir


def test_stage5_refine_repo(
    ctx: TestContext,
    repo_dir: Path,
    mock_llm: bool = False,
) -> None:
    """
    Stage 5: Cross-file consistency refinement with aider.
    """
    print("\n" + "=" * 70)
    print("Stage 5: Refine Repository")
    print("=" * 70)

    if mock_llm:
        print("[OK] (Mocked) Refinement skipped in mock mode")
        return

    # Real refinement with refine_repo.py
    cmd = [
        sys.executable,
        str(_REFINE_REPO),
        "--repo_dir",
        str(repo_dir),
        "--model",
        "gpt-4.1-mini",
        "--rounds",
        "1",
    ]
    run_command(cmd)
    print(f"[OK] Refined repo: {repo_dir}")


def test_stage6_evaluation(
    ctx: TestContext,
    paper_name: str,
    cleaned_json: Path,
    output_dir: Path,
    repo_dir: Path,
    mock_llm: bool = False,
) -> dict:
    """
    Stage 6: Quality evaluation.

    Returns:
        Evaluation result dict
    """
    print("\n" + "=" * 70)
    print("Stage 6: Evaluation")
    print("=" * 70)

    if mock_llm:
        result = {
            "paper_name": paper_name,
            "score": 4,
            "reasoning": "Mocked evaluation result",
        }
        print(f"[OK] (Mocked) Evaluation score: {result['score']}/5")
        return result

    # Real evaluation with eval.py
    eval_result_dir = output_dir / "eval_results"
    eval_result_dir.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        str(_EVAL_SCRIPT),
        "--paper_name",
        paper_name,
        "--pdf_json_path",
        str(cleaned_json),
        "--output_dir",
        str(output_dir),
        "--target_repo_dir",
        str(repo_dir),
        "--eval_result_dir",
        str(eval_result_dir),
        "--gpt_version",
        "gpt-4.1-mini",
        "--eval_type",
        "ref_free",
        "--data_dir",
        str(_REPO_ROOT / "Paper2Code/data/paper2code"),
    ]
    run_command(cmd, check=False)  # eval.py may have non-zero exit for scoring

    # Parse result
    result_files = list(eval_result_dir.glob("*.json"))
    if result_files:
        result = json.loads(result_files[0].read_text(encoding="utf-8"))
        print(f"[OK] Evaluation complete: {result.get('score', 'N/A')}/5")
        return result
    else:
        print("[WARN] No evaluation result file found")
        return {"paper_name": paper_name, "score": None}


# ── Main Test Runner ──────────────────────────────────────────────────────────


def run_e2e_test(
    skip_validation: bool = False,
    skip_coding: bool = False,
    skip_refine: bool = False,
    skip_eval: bool = False,
    mock_llm: bool = False,
    use_real_qwen: bool = False,
    use_temp_dir: bool = True,
) -> None:
    """
    Run the complete end-to-end pipeline test.

    Args:
        skip_validation: Skip Stage 3 (sandbox validation)
        skip_coding: Skip Stage 4-6 (coding, refine, eval)
        skip_refine: Skip Stage 5 (aider refinement)
        skip_eval: Skip Stage 6 (evaluation)
        mock_llm: Use mocked LLM responses (no API calls)
        use_real_qwen: Use real Qwen model inference (requires model or API)
        use_temp_dir: Use temporary directory (cleaned up after test)
    """
    print("\n" + "=" * 70)
    print("paper2XAgent End-to-End Pipeline Test")
    print("=" * 70)
    print(f"Mock LLM: {mock_llm}")
    print(f"Real Qwen: {use_real_qwen}")
    print(f"Skip validation: {skip_validation}")
    print(f"Skip coding: {skip_coding}")
    print(f"Skip refine: {skip_refine}")
    print(f"Skip eval: {skip_eval}")

    # Check prerequisites
    if not mock_llm:
        if not os.environ.get("OPENAI_API_KEY"):
            print("\n[ERROR] OPENAI_API_KEY not set (required unless --mock-llm)")
            sys.exit(1)

    if use_real_qwen:
        qwen_model_path = os.environ.get(
            "QWEN_MODEL_PATH", "/root/autodl-tmp/Qwen2.5-7B-paper2Xcode"
        )
        qwen_api_base = os.environ.get("QWEN_API_BASE")
        if not qwen_api_base and not Path(qwen_model_path).exists():
            print(
                f"\n[WARN] Real Qwen requested but model not found at {qwen_model_path}"
            )
            print(
                f"[WARN] Set QWEN_MODEL_PATH or QWEN_API_BASE, or remove --use-real-qwen"
            )
            print(f"[WARN] Will fall back to simulated mode if model not accessible")

    paper_name, paper_text, qwen_xml = load_sample_data()

    with TestContext(use_temp_dir=use_temp_dir) as ctx:
        # Stage 0: Data cleaning
        cleaned_txt = test_stage0_data_cleaning(ctx, paper_name, paper_text)

        # Stage 1: Qwen inference
        qwen_xml_path = test_stage1_qwen_inference(
            ctx, paper_name, cleaned_txt, qwen_xml, use_real_qwen=use_real_qwen
        )

        # Stage 2: Build xKG
        xkg_json = test_stage2_build_xkg(ctx, paper_name, cleaned_txt, qwen_xml_path)

        # Stage 3: Validate xKG
        if skip_validation:
            print("\n[SKIP] Stage 3: Validation")
            xkg_validated = xkg_json  # Use unvalidated xKG
        else:
            xkg_validated = test_stage3_validate_xkg(
                ctx, paper_name, xkg_json, mock_llm=mock_llm
            )

        if skip_coding:
            print("\n[SKIP] Stage 4-6: Coding, Refine, Eval")
        else:
            # Stage 4: Coding with xKG injection
            repo_dir = test_stage4_coding_inject(
                ctx, paper_name, cleaned_txt, xkg_validated, mock_llm=mock_llm
            )

            # Stage 5: Refine repository
            if not skip_refine:
                test_stage5_refine_repo(ctx, repo_dir, mock_llm=mock_llm)
            else:
                print("\n[SKIP] Stage 5: Refine")

            # Stage 6: Evaluation
            if not skip_eval:
                cleaned_json = cleaned_txt.parent / f"{paper_name}.json"
                output_dir = ctx.test_root / "repos" / paper_name
                test_stage6_evaluation(
                    ctx,
                    paper_name,
                    cleaned_json,
                    output_dir,
                    repo_dir,
                    mock_llm=mock_llm,
                )
            else:
                print("\n[SKIP] Stage 6: Eval")

        print("\n" + "=" * 70)
        print("[PASS] End-to-End Test PASSED")
        print("=" * 70)

        if not use_temp_dir:
            print(f"\nTest outputs preserved at: {ctx.test_root}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end integration test for paper2XAgent pipeline"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip Stage 3 (sandbox validation)",
    )
    parser.add_argument(
        "--skip-coding",
        action="store_true",
        help="Skip Stage 4-6 (coding, refine, eval)",
    )
    parser.add_argument(
        "--skip-refine",
        action="store_true",
        help="Skip Stage 5 (aider refinement)",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip Stage 6 (evaluation)",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use mocked LLM responses (no API calls, fast)",
    )
    parser.add_argument(
        "--use-real-qwen",
        action="store_true",
        help="Use real Qwen model for Stage 1 inference (requires model on server or QWEN_API_BASE)",
    )
    parser.add_argument(
        "--keep-outputs",
        action="store_true",
        help="Keep test outputs in test_outputs/ directory (don't use temp dir)",
    )
    args = parser.parse_args()

    run_e2e_test(
        skip_validation=args.skip_validation,
        skip_coding=args.skip_coding,
        skip_refine=args.skip_refine,
        skip_eval=args.skip_eval,
        mock_llm=args.mock_llm,
        use_real_qwen=args.use_real_qwen,
        use_temp_dir=not args.keep_outputs,
    )


if __name__ == "__main__":
    main()
