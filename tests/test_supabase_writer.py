"""Unit tests for crawler/supabase_writer.py"""
import unittest
from unittest.mock import patch, MagicMock
import os


class TestWriteArticles(unittest.TestCase):
    def test_write_articles_empty(self):
        """articles=[] should return 0 without calling client"""
        from crawler.supabase_writer import write_articles
        with patch("crawler.supabase_writer.get_client") as mock_get_client:
            result = write_articles([])
            mock_get_client.assert_not_called()
            self.assertEqual(result, 0)

    def test_write_articles_returns_count(self):
        """mock client returning 2 data rows should return 2"""
        from crawler.supabase_writer import write_articles
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}, {"id": 2}]
        (
            mock_client.table.return_value
            .upsert.return_value
            .execute.return_value
        ) = mock_response

        with patch("crawler.supabase_writer.get_client", return_value=mock_client):
            result = write_articles([{"source_url": "http://a.com"}, {"source_url": "http://b.com"}])
            self.assertEqual(result, 2)


class TestWriteSocialPosts(unittest.TestCase):
    def test_write_social_posts_empty(self):
        """posts=[] should return 0 without calling client"""
        from crawler.supabase_writer import write_social_posts
        with patch("crawler.supabase_writer.get_client") as mock_get_client:
            result = write_social_posts([])
            mock_get_client.assert_not_called()
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
