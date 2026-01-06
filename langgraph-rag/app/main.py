# app/main.py
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import api_router
from app.api.routes.evaluation_routes import router as evaluation_router
from app.config import settings, get_settings
from app.database import create_tables
from app.dependencies import (
    get_model_manager,
    get_embedding_service,
    get_graph_service,
    get_vector_store_service,
    get_evaluation_service,
    get_bert_evaluation_service,
    get_collection_health_service
)

# Configure logging based on settings
log_level = settings.log_level.upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info(f"Logging configured at {log_level} level")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting LangGraph RAG API...")

    # Create database tables
    create_tables()
    logger.info("Database tables created")

    try:
        from app.evaluation.models import Base as EvaluationBase
        from app.database import engine
        EvaluationBase.metadata.create_all(bind=engine)
        logger.info("Evaluation database tables created")
    except Exception as e:
        logger.warning(f"Error creating evaluation tables: {e}")

    # Initialize model manager and check health
    model_manager = get_model_manager()
    health_status = model_manager.health_check()
    logger.info(f"Model health check: {health_status}")

    # Initialize services
    embedding_service = get_embedding_service()
    vector_store_service = get_vector_store_service()
    graph_service = get_graph_service()

    try:
        evaluation_service = get_evaluation_service()
        logger.info("Evaluation service initialized")

        # Check BERT Score availability
        bert_service = get_bert_evaluation_service()
        if bert_service.is_available():
            logger.info(f"BERT Score service available with model: {bert_service.model_type}")
        else:
            logger.warning("BERT Score service not available - install bert-score package")

    except Exception as e:
        logger.warning(f"Error initializing evaluation service: {e}")

    logger.info("All services initialized")

    # Collection health check at startup
    try:
        from app.database import SessionLocal

        health_service = get_collection_health_service()

        # Chroma Collections auflisten
        chroma_collections = embedding_service.list_collections()
        logger.info(f"Found {len(chroma_collections)} Chroma collections")

        # Health Check für alle DB Collections
        db = SessionLocal()
        try:
            summary = health_service.check_all_collections(db)
            logger.info(
                f"Collection Health Check: {summary['total']} total, "
                f"{summary['healthy']} healthy, {summary['needs_rebuild']} need rebuild"
            )

            if summary['needs_rebuild'] > 0:
                logger.warning(
                    f"⚠️  {summary['needs_rebuild']} collections need rebuild. "
                    f"Use the frontend 'Rebuild' button to fix."
                )
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"Error during collection health check: {e}")

    yield

    # Shutdown
    logger.info("Shutting down LangGraph RAG API...")


# Create FastAPI application
app = FastAPI(
    title="LangGraph RAG API",
    description="An intelligent document retrieval and question-answering system using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LangGraph RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check(
        settings: settings = Depends(get_settings),
        model_manager=Depends(get_model_manager)
):
    """Health check endpoint"""
    start_time = time.time()

    # Check model health
    model_health = model_manager.health_check()

    # Check database connection
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_health = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_health = False

    evaluation_health = False
    bert_available = False
    try:
        evaluation_service = get_evaluation_service()
        bert_service = get_bert_evaluation_service()

        evaluation_health = True
        bert_available = bert_service.is_available()

    except Exception as e:
        logger.error(f"Evaluation health check failed: {e}")

    response_time = (time.time() - start_time) * 1000

    return {
        "status": "healthy" if db_health and all(model_health.values()) else "unhealthy",
        "timestamp": time.time(),
        "response_time_ms": round(response_time, 2),
        "components": {
            "database": db_health,
            "models": model_health,
            "evaluation_system": evaluation_health,
            "bert_score": bert_available
        },
        "settings": {
            "ollama_base_url": settings.ollama_base_url,
            "models_configured": list(settings.ollama_models.keys())
        }
    }


@app.get("/models")
async def list_models(model_manager=Depends(get_model_manager)):
    """List available models"""
    return {
        "available_models": model_manager.list_available_models(),
        "model_health": model_manager.health_check()
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )