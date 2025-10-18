"""Tests for configuration loading."""

import unittest
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servbot.config import load_cerebras_key, get_data_dir


class TestConfig(unittest.TestCase):
    """Test cases for configuration functions."""

    def test_get_data_dir(self):
        """Test getting data directory path."""
        data_dir = get_data_dir()
        self.assertIsInstance(data_dir, Path)
        self.assertTrue(str(data_dir).endswith("data"))

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', return_value='CEREBRAS_KEY = "test_key_123"')
    def test_load_cerebras_key_success(self, mock_read, mock_exists):
        """Test successful Cerebras key loading."""
        key = load_cerebras_key()
        self.assertEqual(key, "test_key_123")

    @patch('pathlib.Path.exists', return_value=False)
    def test_load_cerebras_key_file_not_found(self, mock_exists):
        """Test Cerebras key loading when file doesn't exist."""
        key = load_cerebras_key()
        self.assertIsNone(key)

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', return_value='OTHER_KEY = "value"')
    def test_load_cerebras_key_not_found_in_file(self, mock_read, mock_exists):
        """Test when CEREBRAS_KEY not found in file."""
        key = load_cerebras_key()
        self.assertIsNone(key)

    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.read_text', side_effect=Exception("Read error"))
    def test_load_cerebras_key_read_error(self, mock_read, mock_exists):
        """Test error handling when reading file."""
        key = load_cerebras_key()
        self.assertIsNone(key)


if __name__ == "__main__":
    unittest.main()

