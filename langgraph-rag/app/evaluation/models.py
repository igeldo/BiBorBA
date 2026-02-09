"""
Database models for answer evaluation system
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class AnswerEvaluation(Base):
    """Store evaluations of generated answers"""
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(255), index=True)
    question_text = Column(Text, nullable=False)
    stackoverflow_question_id = Column(Integer, nullable=True)
    graph_type = Column(String(50), index=True, default="adaptive_rag")
    graph_execution_id = Column(Integer, ForeignKey("graph_executions.id"), nullable=True)

    generated_answer = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=True)

    bert_precision = Column(Float, nullable=True)
    bert_recall = Column(Float, nullable=True)
    bert_f1 = Column(Float, nullable=True)
    bert_model_type = Column(String(100), default="bert-base-uncased")

    manual_rating = Column(Integer, nullable=True)
    manual_comment = Column(Text, nullable=True)
    evaluator_name = Column(String(100), nullable=True)

    llm_correctness_score = Column(Float, nullable=True)
    llm_correctness_model = Column(String(100), nullable=True)

    model_config = Column(JSON, default={})
    processing_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    llm_model = Column(String(100), nullable=True, index=True)
    embedding_model = Column(String(100), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)

    graph_execution = relationship("GraphExecution")

    def __repr__(self):
        return f"<AnswerEvaluation(id={self.id}, bert_f1={self.bert_f1}, manual_rating={self.manual_rating})>"