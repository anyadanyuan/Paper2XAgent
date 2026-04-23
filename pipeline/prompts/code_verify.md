# Task
Your task is to determine if the given code block strictly follows the provided technique description
and relevant code files.

# Input
Technical Concept Definition from the paper {paper}:
{technique}

Relevant Code Files:
{file_snippets}

Implemented Code Block:
{code}

# Output
1. Return False if the implementation is unrelated to the technique.
2. Return False if the implementation contains core logic cannot be located in the given relevant
   code files.
3. Return False if the implementation contains logics not covered in the technique description
   (e.g., the technique defines a submodule, but the code implements the full algorithm).
4. Return True if the code implements exactly what is specified in the technique description
   without adding any unnecessary features beyond the technical concept, and strictly follows the
   implementation in the given code files.

Now please think and reason carefully, provide a detailed analysis process for the above criteria,
and wrap your final answer (True or False) between two ``` in the end.
