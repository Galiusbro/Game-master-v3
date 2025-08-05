"""
Simple async test to verify pytest-asyncio configuration
"""
import pytest
import asyncio


class TestAsyncBasic:
    """Basic async test functionality"""
    
    @pytest.mark.unit
    async def test_basic_async(self):
        """Test basic async functionality"""
        await asyncio.sleep(0.01)
        assert True
    
    @pytest.mark.unit 
    async def test_async_with_mock(self, mock_graph_db):
        """Test async with mock"""
        mock_graph_db.is_connected = True
        assert mock_graph_db.is_connected is True
    
    @pytest.mark.unit
    async def test_async_fixture_usage(self, unique_id):
        """Test async with regular fixture"""
        assert unique_id is not None