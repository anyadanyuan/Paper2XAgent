#set document(title: "基于论文文本自动生成核心算法代码的微调模型", author: "但杰 蒋佳媛 高鑫彤 徐媛")
#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2cm),
  numbering: none,
)
#set text(
  font: ("New Computer Modern", "SimSun"),
  size: 10.5pt,
  lang: "zh",
)
#set par(
  justify: true,
  first-line-indent: 2em,
  leading: 0.8em,
)

// 标题
#align(center)[
  #text(size: 16pt, weight: "bold")[
    基于论文文本自动生成核心算法代码的微调模型
  ]
  #v(0.3em)
  #text(size: 10pt)[
    但杰 蒋佳媛 高鑫彤 徐媛
  ]
]

#v(0.5em)

// 1. 选题
#text(weight: "bold", size: 11pt)[一、选题]

#par(first-line-indent: 0em)[
  本项目旨在通过微调大语言模型，实现从论文文本到论文算法 PyTorch 代码的自动生成。
]

#v(0.4em)

// 2. 数据
#text(weight: "bold", size: 11pt)[二、数据来源与处理]

#par(first-line-indent: 0em)[
  *数据来源*：Paper2Code 数据集，包含 90 条高质量论文-代码对（覆盖 CV、NLP、RL 等多个领域）。每条样本包含：论文 Abstract + Method 部分 + GitHub 官方实现的核心模型代码（由大模型进行提取）。
]

#par(first-line-indent: 0em)[
  *数据处理*：(1) 清洗论文 PDF，提取纯文本；(2) 从 GitHub 仓库提取核心模型文件；(3) 转换为 Alpaca 格式（Instruction + Input + Output），其中 Instruction 为生成任务描述，Input 为论文文本，Output 为结构化 XML 包装的代码。
]

#v(0.4em)

// 3. 模型
#text(weight: "bold", size: 11pt)[三、模型选择]

#par(first-line-indent: 0em)[
  *基座模型*：Qwen2.5-Coder-7B-Instruct。
]

#v(0.4em)

// 4. 微调
#text(weight: "bold", size: 11pt)[四、微调技术]

#par(first-line-indent: 0em)[
  *微调方法*：LoRA (Low-Rank Adaptation)，使用 QLoRA 4-bit 量化技术。
]

#par(first-line-indent: 0em)[
  *训练框架*：LLaMA-Factory。
]

#v(0.4em)

// 5. 评测
#text(weight: "bold", size: 11pt)[五、评测指标]

#par(first-line-indent: 0em)[
  *(1) 可运行性*（Execution）
]
- XPR（可执行率）：代码在沙盒中直接执行成功的比例
- SAR（独立运行性）：在隔离环境中（无预注入依赖）执行成功的比例
- SYR（语法正确率）：代码能通过 AST 语法解析的比例

#par(first-line-indent: 0em)[
  *(2) 忠实度*（Fidelity）
]
- PCR（论文组件覆盖率）：生成代码包含论文技术组件的比例（LLM 辅助提取 + 规则匹配）
- AAR（API 对齐率）：与参考代码的 PyTorch API 调用重合度
- CodeBERTScore：生成代码与参考代码的语义相似度

#par(first-line-indent: 0em)[
  最终评分将来自于以上指标的加权平均。
]

#v(0.4em)

// 6. 进度与分工
#text(weight: "bold", size: 11pt)[六、进度与分工]

#par(first-line-indent: 0em)[
  *已完成工作*：
]
- 数据清洗与格式转换（90 条样本）
- 微调训练（8 epochs，LoRA 适配器已保存）
- 评测系统构建与测试

#par(first-line-indent: 0em)[
  *后续计划*：
]
- 构建独立测试集
- 在测试集上运行完整评测

#par(first-line-indent: 0em)[
  *分工*：\
  数据处理与微调训练（高鑫彤，但杰）\
  测试集构建与实验分析（徐媛，蒋佳媛）\
  评测系统开发（但杰，蒋佳媛）
]

#v(0.5em)

#align(center)[
  #text(size: 9pt, style: "italic")[
    项目代码库：github.com/paper2XAgent | 提交日期：2026-04-23
  ]
]
