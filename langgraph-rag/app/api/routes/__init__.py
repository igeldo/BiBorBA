"""
Aggregates all API routers for easy integration in main.py
"""

from fastapi import APIRouter

from app.api.routes import query, stackoverflow, scraper, collection_management, batch_queries, comparison_routes, export_routes

api_router = APIRouter()

api_router.include_router(query.router)
api_router.include_router(stackoverflow.router)
api_router.include_router(scraper.router)
api_router.include_router(collection_management.router)
api_router.include_router(batch_queries.router)
api_router.include_router(comparison_routes.router)
api_router.include_router(export_routes.router)

__all__ = ["api_router", "query", "stackoverflow", "scraper", "collection_management", "batch_queries", "comparison_routes", "export_routes"]