# Task
Your task is to analyze a list of code files retrieved from a GitHub repository, and identify which
files are directly relevant to the implementation of a specific technical concept defined in an
academic paper {paper}.

# Input
1. Technical Concept Definition from the paper {paper}: {technique}
2. Overview of the Code repository: {overview}
3. Relevant Code Files: {file_snippets}

# Output
Return a list of filenames formatted as ["xx", "xx", ...], sorted in descending order of relevance of
the technical concept.
1. Exclude any file not DIRECTLY correspond to the concrete implementation and configuration
   of this technique (e.g., tests, documentation, other technique implementation).
2. Confirm that a direct implementation exists within your provided file list. If no such implementation
   can be found, return None.
3. Return the list even if there's only one file.

Now please think and reason carefully, and wrap your final answer between two ``` in the end.
