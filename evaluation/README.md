# Evaluation - 独立评测项目

用于评测微调模型（Qwen2.5-Coder-7B-SFT）与基座模型（Qwen2.5-Coder-7B-Instruct）在 paper-to-code 任务上的性能对比。

**重要特性**：
- ✅ 完全独立于 `paper2XAgent` pipeline
- ✅ 不依赖训练集（需单独构建测试集）
- ✅ 支持本地模型加载和 vLLM API 调用
- ✅ 自动缓存和断点续评
- ✅ 完整的评测指标体系

---

## 评测指标

### 可运行性指标（Execution）

| 指标 | 缩写 | 定义 |
|------|------|------|
| 可执行率 | XPR | 代码在沙盒中执行成功（exit_code=0）的比例 |
| 独立运行性 | SAR | 在隔离环境（无预注入变量）中执行成功的比例 |
| 语法正确率 | SYR | 代码能通过 `ast.parse()` 的比例 |

### 忠实度指标（Fidelity）

| 指标 | 缩写 | 定义 |
|------|------|------|
| 论文组件覆盖率 | PCR | 生成代码包含论文技术组件的比例 |
| API 调用对齐率 | AAR | 与参考代码的 PyTorch API 使用重合度 |
| 代码语义相似度 | CodeBERTScore | 与参考代码的 CodeBERT embedding 相似度 |

### 综合评分

```
execution_score = 0.4 * XPR + 0.4 * SAR + 0.2 * SYR
fidelity_score = 0.5 * PCR + 0.3 * CodeBERTScore + 0.2 * AAR
overall_score = 0.5 * execution_score + 0.5 * fidelity_score
```

---

## 快速开始

### 1. 安装依赖

```bash
cd evaluation/
pip install -r requirements.txt
```

**可选依赖**：
- `code-bert-score`: 用于 CodeBERTScore 计算（推荐）
- `openai`: 用于 PCR 组件提取（使用 OpenAI API 时需要）

### 2. 准备测试集

测试集格式（JSON）：

```json
[
  {
    "paper_id": "unique_id",
    "paper_text": "[Abstract]...\n\n[Method]...",
    "ref_code": "import torch\n...",
    "paper_title": "Paper Name",
    "github_url": "https://github.com/..."
  }
]
```

**重要**：
- 测试集需与训练集完全独立（无交集）
- `ref_code` 可选，用于 AAR 和 CodeBERTScore 计算
- `paper_text` 建议包含 Abstract + Method 部分

### 3. 评测微调模型

```bash
python evaluate.py \
    --model_path /path/to/Qwen2.5-7B-paper2Xcode \
    --dataset /path/to/test_set.json \
    --output_dir outputs/eval/finetuned \
    --max_tokens 2048
```

### 4. 评测基座模型

```bash
python evaluate.py \
    --model_path Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset /path/to/test_set.json \
    --output_dir outputs/eval/baseline \
    --max_tokens 2048
```

### 5. 生成对比报告

```bash
python compare.py \
    --finetuned outputs/eval/finetuned/summary.json \
    --baseline outputs/eval/baseline/summary.json \
    --output outputs/eval/comparison.md
```

---

## 高级用法

### 使用 vLLM API 加速推理

```bash
# 1. 启动 vLLM 服务器
vllm serve Qwen/Qwen2.5-Coder-7B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype bfloat16

# 2. 使用 API 模式评测
python evaluate.py \
    --model_path Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset /path/to/test_set.json \
    --output_dir outputs/eval/baseline \
    --use_api \
    --api_base http://localhost:8000/v1
```

### 断点续评

```bash
# 使用 --resume 参数从上次中断处继续
python evaluate.py \
    --model_path /path/to/model \
    --dataset /path/to/test_set.json \
    --output_dir outputs/eval/finetuned \
    --resume
```

### 配置 OpenAI API（用于 PCR 组件提取）

```bash
# 设置环境变量
export OPENAI_API_KEY="sk-..."

# 或在代码中配置
# 默认使用 gpt-4o-mini，每篇论文调用一次
```

---

## 输出结构

```
outputs/eval/
├── finetuned/
│   ├── results.jsonl          # 每个样本的详细结果
│   ├── summary.json           # 汇总统计
│   └── component_cache/       # 论文组件清单缓存
│       └── paper_id.json
└── baseline/
    ├── results.jsonl
    ├── summary.json
    └── component_cache/
```

### results.jsonl 格式

每行一个样本的 JSON：

```json
{
  "paper_id": "sample_001",
  "success": true,
  "pred_code": "import torch\n...",
  "execution": {
    "xpr": true,
    "sar": false,
    "syr": true,
    "exit_code_xpr": 0,
    "stderr_xpr": "",
    ...
  },
  "fidelity": {
    "pcr": 0.75,
    "aar": 0.6,
    "codebertscore": 0.65,
    "component_hits": ["module:nn.Linear", ...],
    "missing_components": ["pattern:residual_connection"]
  }
}
```

### summary.json 格式

```json
{
  "total_samples": 50,
  "valid_samples": 48,
  "xpr": 0.65,
  "sar": 0.52,
  "syr": 0.83,
  "pcr_avg": 0.70,
  "aar_avg": 0.55,
  "codebertscore_avg": 0.60,
  "execution_score": 0.604,
  "fidelity_score": 0.615,
  "overall_score": 0.6095
}
```

---

## 目录结构

```
evaluation/
├── evaluate.py                # 主评测脚本（CLI入口）
├── compare.py                 # 对比报告生成
├── requirements.txt           # 独立依赖
├── README.md                  # 本文档
├── evaluators/                # 各指标实现
│   ├── __init__.py
│   ├── execution_eval.py      # XPR, SAR, SYR
│   ├── fidelity_eval.py       # PCR, AAR, CodeBERTScore
│   └── paper_extractor.py     # LLM 提取论文组件清单
└── utils/
    ├── __init__.py
    ├── code_parser.py         # 从 XML/文本提取代码
    ├── sandbox.py             # 沙盒执行
    └── model_loader.py        # 统一加载基座/微调模型
```

---

## 关键设计决策

### 为什么独立于 pipeline？

- 本评测用于**另一个项目**的微调效果验证
- 避免耦合：不调用 `build_xkg.py`、`validate_xkg.py` 等 pipeline 模块
- 最小复用：仅从 `validate_xkg.py` **复制**沙盒执行逻辑（不导入）
- 独立演进：评测指标和主项目可以各自迭代

### 为什么不用训练集？

- **数据泄露**：微调模型在训练集上见过输入输出，评测结果会虚高
- **泛化能力**：需要评估模型对未见论文的生成能力
- **学术规范**：严肃的模型对比必须使用独立测试集

### PCR 中的 LLM 使用策略

| 阶段 | LLM 角色 | 调用频率 |
|------|---------|---------|
| 组件清单提取 | 从论文提取结构化要求 | 每篇论文 1 次，结果缓存 |
| 代码评分 | 无，纯规则匹配 | 零次 |

**成本估算**：50 篇测试论文 × 1 次 API 调用 ≈ $0.05（使用 gpt-4o-mini）

---

## 预期结果

| 指标 | 基座模型预期 | 微调模型预期 | 说明 |
|------|------------|------------|------|
| XPR | 20-40% | 60-80% | 微调学会了完整可运行代码模式 |
| SAR | 10-30% | 50-70% | 微调输出自包含代码 |
| SYR | 40-60% | 80-95% | 微调学会了正确语法结构 |
| PCR | 30-50% | 60-80% | 微调强化了技术细节复现 |

**成功标准**：
- 最低目标：微调模型 XPR 比基座模型高 **20 个百分点**
- 理想目标：综合评分（XPR + PCR）高 **30 个百分点**

---

## 故障排查

### 问题：`code-bert-score` 安装失败

**解决方案**：
```bash
pip install code-bert-score --no-deps
pip install transformers torch
```

### 问题：CUDA OOM

**解决方案**：
- 使用 vLLM API 模式（推荐）
- 减少 `max_tokens`
- 使用 8-bit 量化：修改 `model_loader.py` 中的 `load_in_8bit=True`

### 问题：沙盒执行超时

**解决方案**：
- 增加超时时间：修改 `ExecutionEvaluator(timeout=120)`
- 检查生成代码是否包含无限循环

### 问题：PCR 组件提取失败

**解决方案**：
- 检查 `OPENAI_API_KEY` 环境变量
- 或跳过 PCR：评测时不设置 API key，PCR 将返回 0.0

---

## 后续工作

- [ ] 构建测试集（20-50 篇论文，与训练集无交集）
- [ ] 优化 PCR 模式匹配规则（根据 pilot 数据调整）
- [ ] 添加错误分类统计（SyntaxError、ImportError 等）
- [ ] 实现可视化图表生成（对比柱状图、雷达图）

---

## 引用

基于日志 `logs/20260423.md` 中的评测方案设计。

---

**最后更新**：2026-04-23
