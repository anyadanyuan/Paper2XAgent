# paper2XAgent Pipeline Tests

This directory contains tests for the paper2XAgent pipeline.

## Test Files

### `test_build_xkg.py`
Unit tests for Stage 2 (xKG building):
- `QwenOutputProvider` XML parsing
- Abstract extraction
- Code node creation
- Technique node creation
- Full `build_xkg` pipeline

**Usage:**
```bash
python pipeline/tests/test_build_xkg.py
```

**Expected output:**
```
============================================================
Running build_xkg tests
============================================================

[test_qwen_output_provider] Parsed 1 files: ['core_model.py']
  PASSED
[test_extract_abstract] Abstract (XXX chars): ...
  PASSED
[test_make_code_node] packages: ['torch', 'numpy']
  PASSED
[test_make_technique_node] node keys: ['name', 'type', 'description', ...]
  PASSED
[test_full_pipeline] xKG: 1 node(s)
  - Core Model | packages: ['torch']
  PASSED

============================================================
All tests passed!
============================================================
```

---

### `test_e2e_pipeline.py`
End-to-end integration test for the complete pipeline (Stage 0-6).

**Features:**
- Tests all 6 stages sequentially
- Validates outputs at each stage
- Supports mocked LLM calls (no API costs)
- Can preserve outputs for inspection
- Granular skip options for different stages

**Usage:**

```bash
# Full test with mocked LLM (fast, no API key needed)
python pipeline/tests/test_e2e_pipeline.py --mock-llm

# Full test with real API calls (requires OPENAI_API_KEY)
python pipeline/tests/test_e2e_pipeline.py

# Test with real Qwen model inference (requires model on server)
python pipeline/tests/test_e2e_pipeline.py --use-real-qwen --mock-llm

# Test only Stage 0-2 (no API calls)
python pipeline/tests/test_e2e_pipeline.py --skip-validation --skip-coding

# Test with preserved outputs for inspection
python pipeline/tests/test_e2e_pipeline.py --mock-llm --keep-outputs

# Skip specific stages
python pipeline/tests/test_e2e_pipeline.py --skip-refine     # Skip Stage 5
python pipeline/tests/test_e2e_pipeline.py --skip-eval       # Skip Stage 6
```

**Test Stages:**

| Stage | Component | Input | Output | API/Model Required |
|-------|-----------|-------|--------|--------------------|
| 0 | Data Cleaning | Raw paper text | `cleaned_output/*.txt` | No |
| 1 | Qwen Inference | Cleaned text | `qwen/*.xml` | No (simulated) / Yes (--use-real-qwen) |
| 2 | Build xKG | Qwen XML + paper text | `xkg/*.json` | No |
| 3 | Validate xKG | xKG JSON | `xkg/*_validated.json` | Yes (or mock) |
| 4 | Coding (xKG inject) | Validated xKG | `repos/*/repo/*.py` | Yes (or mock) |
| 5 | Refine Repository | Generated repo | Modified repo | Yes (or mock) |
| 6 | Evaluation | Generated repo | Score (1-5) | Yes (or mock) |

**Test Modes:**

| Mode | Speed | Cost | Use Case |
|------|-------|------|----------|
| `--mock-llm` | ~5 sec | $0 | Quick validation, CI/CD, development |
| `--use-real-qwen` | ~2 min | $0 (local GPU) | Test real Qwen inference (Stage 1) |
| Real (default) | ~5-10 min | ~$0.50 (API) | Full integration test, pre-deployment |

**`--use-real-qwen` Flag:**

This flag enables real Qwen model inference in Stage 1 instead of using pre-generated data from `train_dataset.json`.

**Requirements:**
- Qwen model available at `/root/autodl-tmp/Qwen2.5-7B-paper2Xcode` (or set `QWEN_MODEL_PATH`)
- OR `QWEN_API_BASE` environment variable set (for vLLM API)
- GPU access (for local inference)

**Example:**
```bash
# On server with Qwen model
python pipeline/tests/test_e2e_pipeline.py --use-real-qwen --mock-llm

# With custom model path
QWEN_MODEL_PATH=/path/to/model python pipeline/tests/test_e2e_pipeline.py --use-real-qwen

# With vLLM API
QWEN_API_BASE=http://localhost:8000/v1 python pipeline/tests/test_e2e_pipeline.py --use-real-qwen
```

**Note:** If the model is not found, the test will automatically fall back to simulated mode with a warning.

**Output Structure:**

When using `--keep-outputs`, outputs are saved to `test_outputs/`:

```
test_outputs/
├── cleaned_output/
│   ├── TestPaper_E2E.txt          # Stage 0 output
│   └── TestPaper_E2E.json         # Minimal JSON for Paper2Code
├── qwen/
│   └── TestPaper_E2E.xml          # Stage 1 output
├── xkg/
│   ├── TestPaper_E2E.json         # Stage 2 output
│   └── TestPaper_E2E_validated.json  # Stage 3 output
└── repos/TestPaper_E2E/
    └── repo/
        ├── config.yaml            # Generated config
        ├── core_model.py          # xKG-injected code
        └── trainer.py             # Generated code
```

**Exit Codes:**
- `0`: All tests passed
- `1`: Test failure or missing prerequisites

**Prerequisites:**
- Python 3.10+
- `train_dataset.json` exists at `Paper2Code/data/paper2code/train_dataset.json`
- `OPENAI_API_KEY` environment variable (unless `--mock-llm`)

---

## Running Tests on Server

After syncing to the server via `scripts/sync_server.sh`, run tests as follows:

```bash
# On the server
cd ~/paper2XAgent

# Unit test (Stage 2)
python pipeline/tests/test_build_xkg.py

# E2E test with real API
export OPENAI_API_KEY=sk-...
python pipeline/tests/test_e2e_pipeline.py

# E2E test with mock (no API key needed)
python pipeline/tests/test_e2e_pipeline.py --mock-llm --keep-outputs
```

---

## Continuous Integration

For CI/CD pipelines, use mocked mode for fast validation:

```yaml
# Example GitHub Actions
- name: Run e2e test
  run: |
    python pipeline/tests/test_e2e_pipeline.py --mock-llm
```

---

## Troubleshooting

**Issue:** `FileNotFoundError: train_dataset.json not found`
- **Solution:** Ensure you're running from the repo root, or `Paper2Code/data/paper2code/train_dataset.json` exists.

**Issue:** `OPENAI_API_KEY not set`
- **Solution:** Use `--mock-llm` flag or set the environment variable.

**Issue:** `ImportError: No module named 'build_xkg'`
- **Solution:** Run from repo root: `python pipeline/tests/test_e2e_pipeline.py`

**Issue:** Test outputs not cleaned up
- **Solution:** By default, outputs use a temp directory and are auto-deleted. Use `--keep-outputs` to preserve them.

---

## Test Development

To add new tests:

1. **Unit tests**: Add to `test_build_xkg.py` or create new `test_<module>.py`
2. **E2E tests**: Extend `test_e2e_pipeline.py` with new stage functions
3. **Mock responses**: Add to `_MOCK_*` constants in `test_e2e_pipeline.py`

Example new stage test:

```python
def test_stage7_deployment(ctx: TestContext, repo_dir: Path, mock_llm: bool = False) -> None:
    """Stage 7: Deploy to production."""
    print("\n" + "="*70)
    print("Stage 7: Deployment")
    print("="*70)
    
    if mock_llm:
        print("[OK] (Mocked) Deployment succeeded")
        return
    
    # Real deployment logic
    ...
```

---

## Related Documentation

- [Project logs](../../logs/): `20260331.md`, `20260401.md`
- [Pipeline scripts](../): `build_xkg.py`, `validate_xkg.py`, etc.
- [Server sync script](../../scripts/sync_server.sh)
