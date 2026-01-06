"""Answer grader node - checks if the answer addresses the question."""

from typing import Dict, Any, Type
from pydantic import BaseModel, Field
import logging

from app.core.graph.nodes.base_grader import BaseGrader, create_grader_node

logger = logging.getLogger(__name__)


class GradeAnswer(BaseModel):
    """Binary score to assess answer addresses question."""
    binary_score: str = Field(description="Answer addresses the question, 'yes' or 'no'")


class AnswerGrader(BaseGrader):
    """Grader that checks if an answer addresses the question."""

    @property
    def grade_model(self) -> Type[BaseModel]:
        return GradeAnswer

    @property
    def grader_name(self) -> str:
        return "Answer Grader"

    def get_prompt(self):
        return self.prompt_manager.get_answer_grader_prompt()

    def prepare_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "question": state["question"],
            "generation": state["generation"]
        }

    def process_result(self, score, state: Dict[str, Any]) -> Dict[str, Any]:
        is_useful = score.binary_score.lower() == "yes"
        logger.info(f"Answer addresses question: {is_useful}")
        return {"addresses_question": is_useful}


def create_answer_grader_node(model_manager, prompt_manager):
    """Factory function for answer grader node."""
    return create_grader_node(AnswerGrader, model_manager, prompt_manager)
