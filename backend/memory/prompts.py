PAPER_MEMORY_PROMPT = """You are a research analyst. Given the following sections from a paper, extract a structured memory.

PAPER: {title} ({year}) by {authors}

SECTIONS:
{sections_text}

Return JSON only:
{{
  "core_claim": "one sentence summary of the paper's main contribution",
  "methodology": "brief description of the approach",
  "key_results": ["result 1", "result 2", "result 3"],
  "limitations": "brief description of limitations",
  "novelty": "what this contributes vs prior work",
  "target_domain": "e.g. NLP, CV, RL, general ML"
}}"""


CONCEPT_MEMORY_PROMPT = """Extract all named technical concepts, methods, and techniques from these paper sections.
For each concept return:
- name: short canonical name
- definition: definition as used in this paper (1-2 sentences)
- introduced_here: true if this paper is the original source of this concept
- related_concepts: list of related concept names mentioned

Return a JSON array only. Do not include generic terms like "neural network" unless specifically defined here.

SECTIONS:
{sections_text}"""


RELATIONAL_MEMORY_PROMPT = """Classify the relationship this paper has with each of its references.
Use these categories:
- foundational: this paper builds directly on this reference as a core prerequisite
- extends: this paper extends or improves upon this reference
- critiques: this paper challenges or finds flaws in this reference
- uses_as_baseline: this paper uses this reference only as a comparison baseline
- agrees_with: this paper corroborates or confirms findings from this reference

PAPER: {paper_title}

REFERENCES (with citation context extracted from paper body):
{references_with_context}

Return JSON array only:
[{{"ref_title": "...", "rel_type": "foundational|extends|critiques|uses_as_baseline|agrees_with", "reason": "one sentence"}}]"""


CLUE_GENERATION_PROMPT = """You are a personal research assistant with memory of all papers the researcher has read.
Below is a summary of their reading history relevant to the query.

[READING MEMORY]
{compressed_memory_block}

[CONCEPT CLUSTERS RELEVANT TO QUERY]
{concept_cluster_summary}

[QUERY]
{user_query}

Generate a memory clue: a preliminary draft answer (150-300 tokens) that recalls relevant papers, their key claims, and any tensions or open questions you remember. Use paper names where possible. Do not retrieve or search — answer only from the memory above.

Also extract:
- mentioned_papers: list of paper identifiers you referenced (author_year format, e.g. "vaswani_2017")
- suggested_terms: 3-6 key search terms that would help retrieve relevant passages

Return JSON only:
{{
  "clue_text": "...",
  "mentioned_papers": ["...", "..."],
  "suggested_terms": ["...", "..."],
  "confidence": 0.0-1.0
}}"""


CONTRADICT_DETECTION_PROMPT = """Do these two papers make opposing claims about "{concept}"?

Paper A: {paper_a_title}
Claim: {claim_a}

Paper B: {paper_b_title}
Claim: {claim_b}

Answer JSON only:
{{"contradicts": true/false, "reason": "one sentence explaining the tension or agreement"}}"""


CLUSTER_NAMING_PROMPT = """Name this research cluster based on the papers it contains. Give a short (3-7 word) descriptive label.

Papers in cluster:
{paper_titles}

Return JSON only: {{"label": "..."}}"""


QUERY_CLASSIFY_PROMPT = """Classify this research query into one of these categories:
- factual_lookup: asking for a specific fact from a specific paper
- cross_paper_synthesis: comparing or contrasting multiple papers
- draft_request: asking to generate written content (literature review, summary, outline)
- timeline_query: asking about how a topic evolved over time

Query: {query}

Return JSON only: {{"intent": "...", "draft_mode": true/false}}"""
