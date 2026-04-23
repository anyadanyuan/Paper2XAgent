# Task
Your task is to transform a collection of disparate source code snippets, which are the official
implementation of a technique component from a research paper {paper}, into a single, self-contained,
and executable code block. The final code block must be clean, well-documented, and easy for
others to understand and run.

# Input
Abstract of the paper {paper}:
{abstract}

Technical Concept Definition from the paper {paper}:
{technique}

Sub-techniques and Associated Code:
{sub_techniques}

Relevant Code Files:
{file_snippets}

# Workflow
1. Analyze: Understand the technique's inputs, outputs and workflow from the paper.
2. Locate: Fully reuse the code of the provided sub-techniques. For any uncovered parts, locate
   the relevant implementation logic from the given code snippets.
3. Refactor: Integrate the extracted code by removing hard-coded values, isolating the core
   algorithm, and standardizing it with proper documentation and type hints.
4. Assemble & Test: Build the final script and add a test block as a runnable example. Ensure
   accuracy and conciseness, avoiding unnecessary output.
5. Documentation: Write a brief and concise documentation of the code logic, configurable
   options, and usage in 5-10 sentences.

# Requirements
- Dependency Management: Ensure all necessary imports and dependencies are included.
- Fidelity to the Original Technique: Strictly follow the description of the given technique to
  organize the code. ONLY focus on implementation that DIRECTLY corresponds to THIS technique!!!
  (e.g., if the technique is a loss function definition, implement only the code for its calculation.
  Ignore all other parts of the algorithm like model definition or training loop). Return None if no
  direct implementation is found.
- Code Encapsulation and Documentation:
  - Encapsulate the core logic of the technique into one or more functions/classes.
  - Every function and class method must include a comprehensive docstring explaining its
    purpose, parameters, and return values.
  - All function arguments and return values must have clear type hints.
  - Preserve original parameters and comments from the source code.
- Reproducibility and Testing:
  - A main execution block, starting with the comment # TEST BLOCK, is required at the end of
    the file, which serves as a practical usage example and a test case.
  - The test case should use parameters from the code repository or paper. If missing, create and
    state your own defaults.
- Fidelity to the Original Logic:
  - You must strictly adhere to the algorithmic logic present in the provided code snippets. Your
    role is to refactor and structure, not to re-implement or invent new logic.
  - Minimal, necessary modifications are permitted (e.g., renaming variables for clarity, adapting
    function signatures for dependency injection), but the core computational steps must remain
    identical to the original author's implementation.
- Documentation of Usage Scenarios: Provide a concise and fluent document of the code module's
  core logic, configurable options, and usage. Limit the description to 5-10 clear and coherent
  sentences.

# Output
1. Implement the technique standalone without relying on external, undefined components. Return
   an executable code block and a corresponding documentation, each wrapped between two ```.
   Example:

   [... Reasoning Steps ...]

   ```python
   [... Core Implementation of the technique ...]
   [... Ignore other relevant techniques ...]
   # TEST BLOCK
   [... Example Usage ...]
   ```

   The brief documentation of the code:
   ```
   [...Brief Documentation ...]
   ```

2. Verify that the generated code does not exceed the scope of the technique's definition. If the
   technique requires integration with other modules to constitute a single code module, return None.
   If no direct implementation of the technique is found in the given code snippets, also return None.

Now, please proceed with the task, following the workflow and adhering to all requirements.
Generate the final code block and documentation wrapped between two ``` separately at the end.
