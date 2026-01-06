"""
Tests für Vector Store Fehlerbehandlung

Testet nur die kritischen Fehlerfälle:
- Nicht existierende Collection
- Unbekannter Collection-Typ
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.database import CollectionConfiguration


class TestCollectionRebuildErrors:
    """Test Fehlerbehandlung bei rebuild_custom_collection"""

    @patch('app.database.SessionLocal')
    @patch('app.services.collection_manager.CollectionManager')
    def test_nonexistent_collection_raises_error(self, mock_cm_class, mock_session):
        """Nicht existierende Collection wirft ValueError"""
        mock_session.return_value = MagicMock()

        mock_manager = MagicMock()
        mock_manager.get_collection.return_value = None
        mock_cm_class.return_value = mock_manager

        from app.core.graph.tools.vector_store import rebuild_custom_collection

        with pytest.raises(ValueError) as excinfo:
            rebuild_custom_collection(99999)

        assert "not found" in str(excinfo.value).lower()

    @patch('app.database.SessionLocal')
    @patch('app.services.collection_manager.CollectionManager')
    def test_unknown_collection_type_raises_error(self, mock_cm_class, mock_session):
        """Unbekannter Collection-Typ wirft ValueError"""
        mock_session.return_value = MagicMock()

        mock_collection = Mock(spec=CollectionConfiguration)
        mock_collection.id = 1
        mock_collection.name = "Unknown"
        mock_collection.collection_type = "xml"  # Nicht unterstützt

        mock_manager = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_cm_class.return_value = mock_manager

        from app.core.graph.tools.vector_store import rebuild_custom_collection

        with pytest.raises(ValueError) as excinfo:
            rebuild_custom_collection(1)

        assert "Unknown collection type" in str(excinfo.value)


class TestGetRetrieverErrors:
    """Test Fehlerbehandlung bei get_custom_collection_retriever"""

    @patch('app.database.SessionLocal')
    @patch('app.services.collection_manager.CollectionManager')
    def test_nonexistent_collection_raises_error(self, mock_cm_class, mock_session):
        """Nicht existierende Collection wirft ValueError"""
        mock_session.return_value = MagicMock()

        mock_manager = MagicMock()
        mock_manager.get_collection.return_value = None
        mock_cm_class.return_value = mock_manager

        from app.core.graph.tools.vector_store import get_custom_collection_retriever

        with pytest.raises(ValueError) as excinfo:
            get_custom_collection_retriever(99999)

        assert "not found" in str(excinfo.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
