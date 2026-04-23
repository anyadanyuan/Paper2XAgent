# Task
Your task is to refine and enhance the description of a technical concept extracted from a research
paper {paper}. The goal is to produce a clear, concise, and comprehensive description that
accurately captures the essence of the technique.

# Input
1. Technical Concept from the paper {paper}: {technique}
2. Relevant Excerpt of this Technique: {excerpt}

# Output
Return a precise and comprehensive description, presented as a single, continuous paragraph
written in a comprehensive, academic style. Avoid using bullet points, numbered lists, or other
form of itemization.
1. Ensure the technique precisely matches the original description. DO NOT alter, expand, or
   reduce the scope of the technique. Ignore other related techniques and only FOCUS ON this
   technique.
2. Strictly adhering to the original description, augment its implementation details based on the
   provided excerpts. All formulas, parameter configurations, and implementation details must be
   extracted from the given excerpts, ensuring strict adherence to them. Avoid any summarization,
   inference, or omission.
3. If the excerpts offer no new information, leave the description unchanged. Your response MUST
   be based solely on the original description and provided excerpts. The inclusion of ANY external
   information or fabricated details is strictly forbidden!!!
4. Ensure that the provided description is precise, complete, and possesses sufficient detail to
   correspond to a specific implementation.

Now please think and reason carefully, and wrap your final answer between two ``` in the end.
