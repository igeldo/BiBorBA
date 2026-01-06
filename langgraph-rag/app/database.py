# app/database.py
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

from app.config import settings

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class QueryLog(Base):
    """Log all queries for analysis and debugging"""
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    question = Column(Text, nullable=False)
    rewritten_question = Column(Text)
    answer = Column(Text, nullable=False)
    confidence_score = Column(Float)

    # Metadata
    model_config = Column(JSON, default={})
    retriever_type = Column(String(50))
    graph_type = Column(String(50), index=True, default="adaptive_rag")  # Graph type used
    documents_retrieved = Column(Integer, default=0)
    processing_time_ms = Column(Integer)

    # Graph execution details
    graph_trace = Column(JSON)
    node_timings = Column(JSON)

    # User rating
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_rating_comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DocumentEmbedding(Base):
    """Track document embeddings for monitoring"""
    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_source = Column(String(500))
    document_hash = Column(String(64), unique=True, index=True)
    embedding_model = Column(String(100))
    vector_store_id = Column(String(255))  # ChromaDB document ID
    document_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now())


class GraphExecution(Base):
    """Track graph execution for monitoring and debugging"""
    __tablename__ = "graph_executions"

    id = Column(Integer, primary_key=True, index=True)
    query_log_id = Column(Integer, index=True)  # Reference to QueryLog
    session_id = Column(String(255), index=True)
    graph_type = Column(String(50), index=True, default="adaptive_rag")  # Graph type executed

    # Execution details
    execution_path = Column(JSON)  # List of nodes executed
    node_timings = Column(JSON)  # Timing for each node
    node_outputs = Column(JSON)  # Optional: outputs from each node for debugging

    # Results
    total_duration_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))


class RetrievedDocument(Base):
    """Store retrieved documents used in evaluations for comparison view"""
    __tablename__ = "retrieved_documents"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("answer_evaluations.id", ondelete="CASCADE"), index=True)
    query_log_id = Column(Integer, ForeignKey("query_logs.id", ondelete="CASCADE"), index=True)
    source = Column(String(50), nullable=False)  # 'pdf' or 'stackoverflow'
    title = Column(Text)
    content_preview = Column(Text)  # First 200 chars
    full_content = Column(Text)
    relevance_score = Column(Float)
    collection_name = Column(String(255))
    document_metadata = Column(JSON)  # Renamed from 'metadata' (reserved in SQLAlchemy)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# StackOverflow Models
class SOQuestion(Base):
    """StackOverflow questions"""
    __tablename__ = "so_questions"

    # PRIMARY KEY: StackOverflow ID (natürliche ID)
    stack_overflow_id = Column(Integer, primary_key=True, autoincrement=False, index=True)

    title = Column(String(500), nullable=False)
    body = Column(Text)
    tags = Column(String(500))  # Comma-separated tags (increased from 200 to 500)
    score = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    creation_date = Column(DateTime)
    last_activity_date = Column(DateTime)
    owner_user_id = Column(Integer, nullable=True)
    owner_display_name = Column(String(200), nullable=True)
    is_answered = Column(Boolean, default=False)
    accepted_answer_id = Column(Integer, nullable=True)  # StackOverflow Answer ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to answers
    answers = relationship("SOAnswer", back_populates="question", cascade="all, delete-orphan")


class SOAnswer(Base):
    """StackOverflow answers"""
    __tablename__ = "so_answers"

    # PRIMARY KEY: StackOverflow ID (natürliche ID)
    stack_overflow_id = Column(Integer, primary_key=True, autoincrement=False, index=True)

    # FOREIGN KEY: Referenz zu SOQuestion.stack_overflow_id
    question_stack_overflow_id = Column(
        Integer,
        ForeignKey("so_questions.stack_overflow_id"),
        nullable=False,
        index=True
    )

    body = Column(Text, nullable=False)
    score = Column(Integer, default=0)
    creation_date = Column(DateTime)
    last_activity_date = Column(DateTime)
    owner_user_id = Column(Integer, nullable=True)
    owner_display_name = Column(String(200), nullable=True)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship to question
    question = relationship("SOQuestion", back_populates="answers")


# Collection Management Models
class CollectionConfiguration(Base):
    """Custom collections for organizing questions"""
    __tablename__ = "collection_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    collection_type = Column(String(50), default="stackoverflow")

    # Statistics
    question_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_rebuilt_at = Column(DateTime(timezone=True))

    # Health Check Fields
    chroma_exists = Column(Boolean, default=False, nullable=False)
    last_health_check = Column(DateTime(timezone=True))
    needs_rebuild = Column(Boolean, default=True, nullable=False)

    # Rebuild Error (set if background rebuild fails)
    rebuild_error = Column(String, nullable=True)

    # Relationship
    questions = relationship("CollectionQuestion", back_populates="collection", cascade="all, delete-orphan")


class CollectionQuestion(Base):
    """Many-to-Many relationship between collections and questions"""
    __tablename__ = "collection_questions"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collection_configurations.id", ondelete="CASCADE"), nullable=False)
    question_stack_overflow_id = Column(
        Integer,
        ForeignKey("so_questions.stack_overflow_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Metadata
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    added_by = Column(String(100))  # Optional: User tracking

    # Relationships
    collection = relationship("CollectionConfiguration", back_populates="questions")
    question = relationship("SOQuestion")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('collection_id', 'question_stack_overflow_id', name='uq_collection_question'),
    )


class CollectionDocument(Base):
    """Many-to-Many relationship for PDF/document-based collections"""
    __tablename__ = "collection_documents"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collection_configurations.id", ondelete="CASCADE"), nullable=False)
    document_path = Column(String(500), nullable=False)  # Relative path in resources/documents
    document_name = Column(String(200), nullable=False)  # Display name
    document_hash = Column(String(64))  # For deduplication

    # Metadata
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    added_by = Column(String(100))  # Optional: User tracking

    # Relationships
    collection = relationship("CollectionConfiguration")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('collection_id', 'document_path', name='uq_collection_document'),
    )


# Database utility functions
def get_db():
    """Dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)


# Logging service functions
class QueryLogService:
    """Service for logging queries"""

    @staticmethod
    def log_query(
            db: Session,
            session_id: str,
            question: str,
            answer: str,
            **metadata
    ) -> QueryLog:
        """Log a query for analysis purposes"""

        query_log = QueryLog(
            session_id=session_id,
            question=question,
            answer=answer,
            **metadata
        )

        db.add(query_log)
        db.commit()
        db.refresh(query_log)
        return query_log

    @staticmethod
    def get_recent_queries(
            db: Session,
            session_id: Optional[str] = None,
            limit: int = 50
    ) -> List[QueryLog]:
        """Get recent queries for analysis"""
        query = db.query(QueryLog)

        if session_id:
            query = query.filter(QueryLog.session_id == session_id)

        return query.order_by(QueryLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_query_statistics(db: Session) -> Dict[str, Any]:
        """Get query statistics for monitoring"""
        from sqlalchemy import func

        stats = db.query(
            func.count(QueryLog.id).label('total_queries'),
            func.avg(QueryLog.processing_time_ms).label('avg_processing_time'),
            func.avg(QueryLog.documents_retrieved).label('avg_documents_retrieved'),
            func.avg(QueryLog.confidence_score).label('avg_confidence_score')
        ).first()

        # Get most common retriever types
        retriever_stats = db.query(
            QueryLog.retriever_type,
            func.count(QueryLog.id).label('count')
        ).group_by(QueryLog.retriever_type).all()

        return {
            "total_queries": stats.total_queries or 0,
            "average_processing_time_ms": round(stats.avg_processing_time or 0, 2),
            "average_documents_retrieved": round(stats.avg_documents_retrieved or 0, 2),
            "average_confidence_score": round(stats.avg_confidence_score or 0, 2),
            "retriever_usage": {r.retriever_type: r.count for r in retriever_stats}
        }