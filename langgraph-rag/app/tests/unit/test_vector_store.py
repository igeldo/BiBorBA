"""
Unit tests for Vector Store error handling.

Tests critical error cases:
- Non-existent collection handling
- Unknown collection type handling
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.database import CollectionConfiguration


class TestCollectionRebuildErrors:
    """Tests for error handling in rebuild_custom_collection."""

    @patch('app.database.SessionLocal')
    @patch('app.services.collection_manager.CollectionManager')
    def test_nonexistent_collection_raises_error(self, mock_cm_class, mock_session):
        """
        Test that rebuilding a non-existent collection raises ValueError.

        Assume:
            - Collection with ID 99999 does not exist
            - CollectionManager.get_collection returns None

        Expect:
            - ValueError is raised
            - Error message contains "not found"
        """
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
        """
        Test that rebuilding a collection with unknown type raises ValueError.

        Assume:
            - Collection exists with an unsupported type ("xml")

        Expect:
            - ValueError is raised
            - Error message contains "Unknown collection type"
        """
        mock_session.return_value = MagicMock()

        mock_collection = Mock(spec=CollectionConfiguration)
        mock_collection.id = 1
        mock_collection.name = "Unknown"
        mock_collection.collection_type = "xml"

        mock_manager = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_cm_class.return_value = mock_manager

        from app.core.graph.tools.vector_store import rebuild_custom_collection

        with pytest.raises(ValueError) as excinfo:
            rebuild_custom_collection(1)

        assert "Unknown collection type" in str(excinfo.value)


class TestGetRetrieverErrors:
    """Tests for error handling in get_custom_collection_retriever."""

    @patch('app.database.SessionLocal')
    @patch('app.services.collection_manager.CollectionManager')
    def test_nonexistent_collection_raises_error(self, mock_cm_class, mock_session):
        """
        Test that getting retriever for non-existent collection raises ValueError.

        Assume:
            - Collection with ID 99999 does not exist
            - CollectionManager.get_collection returns None

        Expect:
            - ValueError is raised
            - Error message contains "not found"
        """
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
