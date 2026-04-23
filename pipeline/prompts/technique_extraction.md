# Task
You are provided with the paper titled {title}. Here are the main sections of the paper: {sections}.
Furthermore, key equations from the paper are provided to help you understand its specific
algorithms: {equations}. Your task is to analyze the provided research paper and identify its
Core Components. For each Component, you must provide a clear, concise, and implementable
definition.

# INSTRUCTIONS
1. Identify Core Components: Read the paper to identify its primary components. A component
is not limited to a single algorithm; it can be a novel methodology, reusable techniques, key
insight/finding, open-source datasets/benchmarks, etc.
2. Categorize Each Component: Assign one of the following types to each component you identify:
   - Methodology: A novel, end-to-end procedure proposed by the paper for solving a problem.
     This can be an entire algorithm or model architecture design that addresses a specific research
     challenge. It must correspond to a systematic and complete end-to-end code implementation.
     When composed of multiple atomic sub-techniques, represent using the "components" field.
     Ensure the methodology can be implemented standalone, instead of a generic theoretical
     definition or a high-level outline of a framework.
   - Technique: A self-contained and algorithmically implementable component, applied within
     the paper's Methodology or Experiment Process. It is either a novel module from this work, or
     a traceable technique from prior research. When composed of multiple atomic sub-techniques,
     represent using the "components" field. Ensure each technique can be implemented standalone,
     requiring NO integration with other modules to constitute a single code module. Exclude
     theoretical points and experimental tricks not directly tied to code implementation. Move
     them to the "Finding" category.
   - Finding: A significant empirical or theoretical insight which can refer to an intriguing
     experimental finding, a powerful theoretical proof, or a promising research direction.
   - Resource: A PUBLICLY available dataset or benchmark originally constructed in this paper.
3. Define and Detail: For each component, provide a detailed definition adhering to the following
rules:
   - Fidelity: All definitions must originate strictly from the provided paper. Do not invent details.
   - Atomicity & Modularity: Each component, whether high-level or a component, should be
     defined as a distinct, self-contained unit. Explain its inputs, core logic, and outputs.
   - Reproducibility: Retain as much original detail as possible. The definition should be
     comprehensive enough for an engineer or researcher to understand and implement it.
   - Structure: If a 'Methodology' or a 'Technique' is composed of smaller 'Technique's, represent
     this hierarchical relationship using nested bullet points. This is crucial for understanding
     how the parts form the whole. Don't list techniques individually if they're already part of a
     larger technique/methodology.

# OUTPUT FORMAT
Organize the extracted techniques into a list of dictionaries, with the final answer wrapped between
two ``` markers. The keys for each dictionary are described below:
1. name: str, the name of the component, expressed as a concise and standardized academic term,
   intended to precisely capture its core identity while facilitating efficient indexing and retrieval
   from other literature.
2. type: str, One of 'Methodology', 'Technique', 'Finding', or 'Resource'.
3. description: str, A detailed, self-contained explanation of the component, focusing on what it
   is, how it works, and its purpose. For implementable items, describe the whole process without
   missing any critical steps and implementation details. For insights, describe the core discovery.
   Maximize the retention of description and implementation details from the original text.
4. components: List[dict], Optional. If the component is a complex 'Methodology' or 'Technique'
   composed of multiple smaller techniques, this field lists its key sub-techniques. Each sub-technique
   listed here must also be defined separately as a complete technique object following this same
   JSON schema (with 'name', 'type' and 'description' as dictionary keys), allowing for hierarchical
   and recursive decomposition. ATTENTION: Only 'Methodology' and 'Technique' can have
   'Technique' as its components!!!

Now please think and reason carefully, and wrap your final answer between two ``` in the end.
