import unittest
from unittest.mock import patch
from src.api.la_liga_api import LaLigaAPI
from src.config import WEEKS_TOTAL

class TestLaLigaAPI(unittest.TestCase):

    def setUp(self):
        self.api = LaLigaAPI(cache_dir='data/test')
        
        # Mock players
        self.players_external = [
            {'id': 'p1', 'nickname': 'n1', 'images': {'transparent': {'256x256': 'i1'}}}, 
            {'id': 'p2', 'nickname': 'n2', 'images': {'transparent': {'256x256': 'i2'}}}
        ]
        self.players_internal = {player['id']: player for player in self.players_external}
        
        # Mock games stats
        self.games_stats_external = [{'id': 'game1'}, {'id': 'game2'}]
        self.games_stats_internal = [self.games_stats_external for _ in range(WEEKS_TOTAL)]

        # Mock cache write
        self.mock_cache_write = patch('src.utils.cache_manager.CacheManager.write_to_cache').start()

    def tearDown(self):
        patch.stopall()

    # GET PLAYER TESTS
    def get_players_test_helper(self, players_prop, cache_return, request_return, force_refresh=False):
        self.api.players = players_prop
        with patch('src.utils.api_manager.APIManager.request') as mock_request, \
             patch('src.utils.cache_manager.CacheManager.get_from_cache') as mock_cache_read:
            mock_cache_read.return_value = cache_return
            mock_request.return_value = request_return

            players = self.api.get_players(force_refresh=force_refresh)

        return players, mock_cache_read, mock_request

    def test_get_players_from_property(self):
        players, mock_cache_read, mock_request = self.get_players_test_helper(self.players_internal, None, None)

        mock_request.assert_not_called()
        mock_cache_read.assert_not_called()
        self.mock_cache_write.assert_not_called()

        self.assertEqual(players, self.players_internal)

    def test_get_players_from_cache(self):
        players, mock_cache_read, mock_request = self.get_players_test_helper(None, self.players_internal, None)

        mock_request.assert_not_called()
        mock_cache_read.assert_called_once()
        self.mock_cache_write.assert_not_called()

        self.assertEqual(players, self.players_internal)
    
    def test_get_players_from_api(self):
        players, mock_cache_read, mock_request = self.get_players_test_helper(None, None, self.players_external)

        mock_request.assert_called_once()
        mock_cache_read.assert_called_once()
        self.mock_cache_write.assert_called_once()

        self.assertEqual(players, self.players_internal)

    def test_get_players_force_refresh(self):
        players, mock_cache_read, mock_request = self.get_players_test_helper('some players', 'some players', self.players_external, force_refresh=True)

        mock_request.assert_called_once()
        mock_cache_read.assert_not_called()
        self.mock_cache_write.assert_called_once()

        self.assertEqual(players, self.players_internal)

    # GET GAMES STATS TESTS
    def get_games_stats_test_helper(self, games_stats_prop, cache_return, request_return, force_refresh=False):
        self.api.games_stats = games_stats_prop
        with patch('src.utils.api_manager.APIManager.request') as mock_request, \
             patch('src.utils.cache_manager.CacheManager.get_from_cache') as mock_cache_read:
            mock_cache_read.return_value = cache_return
            mock_request.return_value = request_return

            games_stats = self.api.get_games_stats(force_refresh=force_refresh)

        return games_stats, mock_cache_read, mock_request
    
    def test_get_games_stats_from_property(self):
        games_stats, mock_cache_read, mock_request = self.get_games_stats_test_helper(self.games_stats_internal, None, None)

        mock_request.assert_not_called()
        mock_cache_read.assert_not_called()
        self.mock_cache_write.assert_not_called()

        self.assertEqual(games_stats, self.games_stats_internal)

    def test_get_games_stats_from_cache(self):
        games_stats, mock_cache_read, mock_request = self.get_games_stats_test_helper(None, self.games_stats_internal, None)

        mock_request.assert_not_called()
        mock_cache_read.assert_called_once()
        self.mock_cache_write.assert_not_called()

        self.assertEqual(games_stats, self.games_stats_internal)
    
    def test_get_games_stats_from_api(self):
        games_stats, mock_cache_read, mock_request = self.get_games_stats_test_helper(None, None, self.games_stats_external)

        assert mock_request.call_count == WEEKS_TOTAL
        mock_cache_read.assert_called_once()
        self.mock_cache_write.assert_called_once()

        self.assertEqual(games_stats, self.games_stats_internal)

    def test_get_games_stats_force_refresh(self):
        games_stats, mock_cache_read, mock_request = self.get_games_stats_test_helper(self.games_stats_internal, self.games_stats_internal, self.games_stats_external, force_refresh=True)

        assert mock_request.call_count == WEEKS_TOTAL
        mock_cache_read.assert_not_called()
        self.mock_cache_write.assert_called_once()

        self.assertEqual(games_stats, self.games_stats_internal)
    
    # TODO get_player_next_week_num
    
    # GET PLAYERS NICKNAMES TESTS
    @patch('src.api.la_liga_api.LaLigaAPI.get_players')
    def test_get_players_nicknames(self, mock_get_players):        
        mock_get_players.return_value = self.players_internal

        nicknames = self.api.get_players_nicknames()
        expected_nicknames = [p['nickname'] for p in self.players_internal.values()]

        mock_get_players.assert_called_once()
        self.assertEqual(nicknames, expected_nicknames)

    # GET PLAYERS IMAGES TESTS
    @patch('src.api.la_liga_api.LaLigaAPI.get_players')
    def test_get_players_images(self, mock_get_players):
        mock_get_players.return_value = self.players_internal

        image = self.api.get_player_image('p1')
        expected_image = 'i1'

        mock_get_players.assert_called_once()
        self.assertEqual(image, expected_image)
    
    def test_get_historical_market_values(self):
        player_id = 'p1'
        expected_market_values = [{'id': 'value1'}, {'id': 'value2'}]
        
        with patch('src.api.la_liga_api.LaLigaAPI.get_players') as mock_get_players, \
             patch('src.api.la_liga_api.LaLigaAPI.api_v3.request') as mock_api_request:
            mock_get_players.return_value = self.players_internal
            mock_api_request.return_value = expected_market_values
            
            market_values = self.api.get_historical_market_values(player_id)
            
        mock_get_players.assert_called_once()
        mock_api_request.assert_called_once_with(f'/player/{player_id}/market-value')
        self.assertEqual(market_values, expected_market_values)
    