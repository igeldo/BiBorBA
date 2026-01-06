# app/api/routes/__init__.py
"""
Aggregiert alle API Router für einfache Integration in main.py
"""

from fastapi import APIRouter

from app.api.routes import query, stackoverflow, collections, scraper, collection_management, batch_queries, comparison_routes

# Haupt-Router, der alle Sub-Router kombiniert
api_router = APIRouter()

# Inkludiere alle thematischen Router
api_router.include_router(query.router)
api_router.include_router(stackoverflow.router)
api_router.include_router(collections.router)
api_router.include_router(scraper.router)
api_router.include_router(collection_management.router)
api_router.include_router(batch_queries.router)
api_router.include_router(comparison_routes.router)

# Optional: Export der einzelnen Router für direkte Verwendung
__all__ = ["api_router", "query", "stackoverflow", "collections", "scraper", "collection_management", "batch_queries", "comparison_routes"]