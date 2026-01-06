"""Base class for grader nodes with common functionality."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from pydantic import BaseModel
import logging

from app.utils.timing import TimingContext

logger = logging.getLogger(__name__)


class BaseGrader(ABC):
    """Abstract base class for all grader nodes.

    Provides common functionality for LLM-based grading:
    - Model and prompt management
    - Grader chain creation (lazy-loaded)
    - Timing instrumentation

    Subclasses must implement:
    - grade_model: The Pydantic model class for structured output
    - grader_name: Name for logging and timing
    - get_prompt(): Return the prompt for this grader
    - prepare_input(state): Extract and format input from state
    - process_result(score, state): Convert score to state updates
    """

    def __init__(self, model_manager, prompt_manager):
        self.model_manager = model_manager
        self.prompt_manager = prompt_manager
        self._grader = None

    @property
    @abstractmethod
    def grade_model(self) -> Type[BaseModel]:
        """Return the Pydantic model class for grading."""
        pass

    @property
    @abstractmethod
    def grader_name(self) -> str:
        """Return the name of this grader for logging."""
        pass

    @abstractmethod
    def get_prompt(self):
        """Return the prompt for this grader."""
        pass

    @abstractmethod
    def prepare_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input dict for the grader from state."""
        pass

    @abstractmethod
    def process_result(self, score, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process grading result and return state updates."""
        pass

    def _get_grader(self):
        """Lazy-load the grader chain."""
        if self._grader is None:
            with TimingContext(f"Get {self.grader_name} model", logger):
                llm = self.model_manager.get_structured_model(
                    "grader",
                    self.grade_model,
                    format="json"
                )
                prompt = self.get_prompt()
                self._grader = prompt | llm
        return self._grader

    def grade(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute grading and return state updates.

        This is the main entry point for grading. Override this method
        if you need custom grading logic (e.g., batch processing).
        """
        grader = self._get_grader()
        grader_input = self.prepare_input(state)

        with TimingContext(f"LLM call: {self.grader_name}", logger):
            score = grader.invoke(grader_input)

        return self.process_result(score, state)


def create_grader_node(grader_class: Type[BaseGrader], model_manager, prompt_manager):
    """Factory function to create a grader node from a BaseGrader subclass.

    Args:
        grader_class: A class that extends BaseGrader
        model_manager: The model manager instance
        prompt_manager: The prompt manager instance

    Returns:
        A callable that can be used as a LangGraph node
    """
    grader = grader_class(model_manager, prompt_manager)
    return grader.grade
