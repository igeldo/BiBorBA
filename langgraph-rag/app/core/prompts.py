# core/prompts.py
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any


class PromptManager:
    """Centralized management of all prompts"""

    # Document Grading
    DOCUMENT_GRADER_SYSTEM = """You are a strict grader assessing whether a retrieved document is truly relevant to answer a user question.

RELEVANCE CRITERIA - A document is ONLY relevant if:
1. It directly addresses the SPECIFIC topic or problem in the question
2. It contains information that would actually help answer the user's EXACT question
3. The content is semantically aligned with the question's intent, not just sharing keywords

REJECTION CRITERIA - Mark as NOT relevant if:
1. The document only shares general keywords (e.g., both mention "SQL" but different topics)
2. The document discusses a related but different concept
3. The document is about a different domain/use-case despite similar terminology

Examples:
- Question: "How to find prime numbers in SQL?" + Document about "Full Text Search in SQL" → NOT relevant (different topic)
- Question: "How to optimize SQL queries?" + Document about "SQL query performance tuning" → relevant (same topic)

RESPONSE FORMAT:
- binary_score: 'yes' if relevant, 'no' if not
- confidence: Your confidence in this assessment (0.0 = pure guess, 1.0 = absolutely certain)
- reasoning: Brief explanation of your decision (1-2 sentences)

CONFIDENCE GUIDELINES:
- 1.0: Document is clearly and directly about the exact question topic
- 0.8-0.9: Document is highly relevant with minor tangential content
- 0.6-0.7: Document is somewhat relevant but not a perfect match
- 0.4-0.5: Borderline relevance, could go either way
- 0.1-0.3: Probably not relevant, weak connection
- 0.0: Completely unrelated"""

    DOCUMENT_GRADER_HUMAN = """Retrieved document:

{document}

User question: {question}

Assess the document's relevance with binary_score, confidence, and reasoning."""

    # Answer Grading
    ANSWER_GRADER_SYSTEM = """You are a grader assessing whether an answer addresses / resolves a question.
Give a binary score 'yes' or 'no'. 'Yes' means that the answer resolves the question."""

    ANSWER_GRADER_HUMAN = "User question: \n\n {question} \n\n LLM generation: {generation}"

    # Hallucination Grading
    HALLUCINATION_GRADER_SYSTEM = """You are a grader assessing whether an LLM generation is factually supported by retrieved documents.

GRADING GUIDELINES:
1. Focus on FACTUAL CONTENT, not exact wording
2. If the answer's key information (SQL queries, explanations, solutions) can be traced back to ANY of the provided documents, answer 'yes'
3. Rephrasing, simplification, or reorganization is ACCEPTABLE - not hallucination
4. Only answer 'no' if the generation contains MAJOR claims that have NO basis in the provided documents

Give a binary score 'yes' or 'no'. 'Yes' = answer is factually supported by these documents."""

    HALLUCINATION_GRADER_HUMAN = "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"

    # Question Rewriting
    QUESTION_REWRITER_SYSTEM = """You are a question re-writer that reformulates questions for better vectorstore retrieval.

IMPORTANT RULES:
1. Keep the SAME semantic meaning as the original question
2. Only rephrase to improve keyword matching, NOT to change what is being asked
3. Preserve ALL technical terms exactly (e.g., "JSON", "MySQL", "index", "array", "PostgreSQL")
4. Do NOT add assumptions or interpretations beyond what the user asked
5. Do NOT expand the scope of the question
6. The rewritten question should still be answerable by the same type of information

GOOD EXAMPLES:
- Original: "How to index JSON array in MySQL?" -> Rewritten: "MySQL JSON array indexing methods and techniques"
- Original: "What is SQL injection?" -> Rewritten: "SQL injection definition explanation prevention"

BAD EXAMPLES (DO NOT DO THIS):
- Original: "How to index JSON array in MySQL?" -> "What are the best database optimization techniques?" (too broad)
- Original: "SQL query performance" -> "Full-stack application optimization" (different topic)

Output ONLY the rewritten question, nothing else."""

    QUESTION_REWRITER_HUMAN = "Original question: {question}\n\nRewritten question:"

    # Answer Generation
    ANSWER_GENERATOR_SYSTEM = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.

IMPORTANT:
- Focus on the user's specific question only
- Do NOT answer unrelated questions from the context

Provide a complete answer that includes:
- A clear explanation of the problem/concept
- The solution (code, query, etc.) if applicable
- Any relevant details that help understanding

If you don't know the answer, just say that you don't know."""

    ANSWER_GENERATOR_HUMAN = "Question: {question} \n\nContext: {context}"

    # Pure LLM (No RAG)
    PURE_LLM_SYSTEM = """You are an assistant for question-answering tasks.
Answer the question to the best of your knowledge based on your training.
If you don't know the answer, just say that you don't know.
Keep the answer concise but informative.
Your answer should include an explanation for the problem and a possible solution when applicable."""

    PURE_LLM_HUMAN = "Question: {question}"

    # Tool Descriptions
    RETRIEVER_TOOL_DESCRIPTION = "Search and retrieve information for sql questions."

    @classmethod
    def get_document_grader_prompt(cls) -> ChatPromptTemplate:
        """Get document relevance grading prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.DOCUMENT_GRADER_SYSTEM),
            ("human", cls.DOCUMENT_GRADER_HUMAN),
        ])

    @classmethod
    def get_answer_grader_prompt(cls) -> ChatPromptTemplate:
        """Get answer quality grading prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.ANSWER_GRADER_SYSTEM),
            ("human", cls.ANSWER_GRADER_HUMAN),
        ])

    @classmethod
    def get_hallucination_grader_prompt(cls) -> ChatPromptTemplate:
        """Get hallucination detection prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.HALLUCINATION_GRADER_SYSTEM),
            ("human", cls.HALLUCINATION_GRADER_HUMAN),
        ])

    @classmethod
    def get_question_rewriter_prompt(cls) -> ChatPromptTemplate:
        """Get question rewriting prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.QUESTION_REWRITER_SYSTEM),
            ("human", cls.QUESTION_REWRITER_HUMAN),
        ])

    @classmethod
    def get_answer_generator_prompt(cls) -> ChatPromptTemplate:
        """Get answer generation prompt"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.ANSWER_GENERATOR_SYSTEM),
            ("human", cls.ANSWER_GENERATOR_HUMAN),
        ])

    @classmethod
    def get_pure_llm_prompt(cls) -> ChatPromptTemplate:
        """Get pure LLM prompt (no RAG context)"""
        return ChatPromptTemplate.from_messages([
            ("system", cls.PURE_LLM_SYSTEM),
            ("human", cls.PURE_LLM_HUMAN),
        ])

    @classmethod
    def get_all_prompts(cls) -> Dict[str, str]:
        """Get all prompt templates for inspection"""
        return {
            "document_grader_system": cls.DOCUMENT_GRADER_SYSTEM,
            "document_grader_human": cls.DOCUMENT_GRADER_HUMAN,
            "answer_grader_system": cls.ANSWER_GRADER_SYSTEM,
            "answer_grader_human": cls.ANSWER_GRADER_HUMAN,
            "hallucination_grader_system": cls.HALLUCINATION_GRADER_SYSTEM,
            "hallucination_grader_human": cls.HALLUCINATION_GRADER_HUMAN,
            "question_rewriter_system": cls.QUESTION_REWRITER_SYSTEM,
            "question_rewriter_human": cls.QUESTION_REWRITER_HUMAN,
            "answer_generator_system": cls.ANSWER_GENERATOR_SYSTEM,
            "answer_generator_human": cls.ANSWER_GENERATOR_HUMAN,
        }


# Global prompt manager instance
prompt_manager = PromptManager()


def get_prompt_manager() -> PromptManager:
    """Dependency for accessing prompt manager"""
    return prompt_manager