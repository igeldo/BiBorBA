# app/evaluation/model_manager.py
"""
Database models for answer evaluation system
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class AnswerEvaluation(Base):
    """Store evaluations of generated answers"""
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to original query/question
    session_id = Column(String(255), index=True)
    question_text = Column(Text, nullable=False)
    stackoverflow_question_id = Column(Integer, nullable=True)  # If from StackOverflow

    # Graph execution reference
    graph_type = Column(String(50), index=True, default="adaptive_rag")  # Graph type used
    graph_execution_id = Column(Integer, ForeignKey("graph_executions.id"), nullable=True)

    # Generated answer details
    generated_answer = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=True)  # Original/best answer for comparison

    # BERT Score evaluation
    bert_precision = Column(Float, nullable=True)
    bert_recall = Column(Float, nullable=True)
    bert_f1 = Column(Float, nullable=True)
    bert_model_type = Column(String(100), default="bert-base-uncased")

    # Manual evaluation
    manual_rating = Column(Integer, nullable=True)  # 1-5 scale
    manual_comment = Column(Text, nullable=True)
    evaluator_name = Column(String(100), nullable=True)

    # Metadata
    model_config = Column(JSON, default={})
    processing_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)  # When manual evaluation was done

    # Relationship
    graph_execution = relationship("GraphExecution")

    def __repr__(self):
        return f"<AnswerEvaluation(id={self.id}, bert_f1={self.bert_f1}, manual_rating={self.manual_rating})>"