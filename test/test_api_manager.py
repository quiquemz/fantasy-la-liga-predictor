import unittest
from unittest.mock import patch
from requests.exceptions import RequestException
from src.utils.api_manager import APIManager


class TestAPIManager(unittest.TestCase):
    def setUp(self):
        self.api_manager = APIManager('https://api.example.com')

    @patch('requests.get')
    def test_request(self, mock):
        mock.return_value.json.return_value = {'key': 'value'}

        response = self.api_manager.request('/test')

        mock.assert_called_once_with('https://api.example.com/test')
        self.assertEqual(response, {'key': 'value'})

    @patch('requests.get')
    def test_request_raises_exception(self, mock):
        mock.side_effect = Exception('Test exception')

        response = self.api_manager.request('/test')

        mock.assert_called_once_with('https://api.example.com/test')
        self.assertEqual(response, None)

    @patch('requests.get')
    def test_request_raises_request_exception(self, mock):
        mock.side_effect = RequestException('Test exception')

        response = self.api_manager.request('/test')

        mock.assert_called_once_with('https://api.example.com/test')
        self.assertEqual(response, None)

