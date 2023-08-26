import os
import pytz

from datetime import datetime

from src.utils.api_manager import APIManager
from src.utils.cache_manager import CacheManager
from src.utils.decorators import load_and_cache, update_and_cache

from src.config import SEASON, WEEKS_TOTAL


class LaLigaAPI(object):

    # HTTP
    HTTPS = os.getenv('HTTPS', 'https://')
    DOMAIN = os.getenv('DOMAIN', 'api.laligafantasymarca.com')

    # V1
    V1 = os.getenv('V1', '/stats/v1')
    HTTPS_DOMAIN_V1 = f'{HTTPS}{DOMAIN}{V1}'
    ROUTE_WEEK = os.getenv('ROUTE_WEEK', '/stats/week')

    # V3
    V3 = os.getenv('V3', '/api/v3')
    HTTPS_DOMAIN_V3 = f'{HTTPS}{DOMAIN}{V3}'
    ROUTE_PLAYERS = os.getenv('ROUTE_PLAYERS', '/players')

    # FILES
    # Get the parent directory of the current file
    PARENT_DIR = os.getenv('PARENT_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/json'))
    PLAYERS_PATH = f'players.{SEASON}.json'
    GAMES_STATS_PATH = f'games_stats.{SEASON}.json'

    # Spain Timezon
    TZ_SPAIN = pytz.timezone('Europe/Madrid')

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = self.PARENT_DIR
            
        self.api_v1 = APIManager(self.HTTPS_DOMAIN_V1)
        self.api_v3 = APIManager(self.HTTPS_DOMAIN_V3)
        self.cache_manager = CacheManager(cache_dir)

    @load_and_cache()
    def get_players(self, force_refresh=False):  # "force_refresh" is used in the decorator
        players = self.api_v3.request(self.ROUTE_PLAYERS)
        return {str(p['id']): p for p in players}

    @load_and_cache()
    def get_games_stats(self, force_refresh=False):  # "force_refresh" is used in the decorator
        return [self.api_v1.request(self.ROUTE_WEEK + '/' + str(w+1)) for w in range(WEEKS_TOTAL)]
    
    def get_player_next_week_num(self, player_id):
        now_spain = datetime.now(self.TZ_SPAIN)
        games_stats = self.get_games_stats()
        team_id = self.get_team(player_id)['id']

        for i, week in enumerate(games_stats):
            for game in week:
                match_date = datetime.fromisoformat(game['matchDate'][:-1]).replace(tzinfo=pytz.UTC)
                local_id = game['local']['id']
                visitor_id = game['visitor']['id']

                if (team_id == local_id or team_id == visitor_id) and match_date >= now_spain:
                    return i+1
             
        return None

    def get_players_nicknames(self):
        players = self.get_players()
        return [p['nickname'] for p in players.values()]
    
    def get_player_image(self, player_id, background='transparent', size='256x256'):
        players = self.get_players()
        return players[player_id]['images'][background][size]

    @update_and_cache('players')
    def get_historical_market_values(self, player_id):
        # NOTE: since values are changing daily, we need to get the latest value from the API
        players = self.get_players()
        player = players[player_id]
        player['historicalMarketValues'] = self.api_v3.request(f'/player/{player_id}/market-value')
        
        return player['historicalMarketValues']
    
    @update_and_cache('players')
    def get_player_stats(self, player_id):
        # NOTE: since values are changing regularly, we need to get the latest value from the API
        players = self.get_players()
        player = players[player_id]
        player.update(self.api_v3.request(f'/player/{player_id}'))

        return player['playerStats']

    def get_team(self, player_id):
        players = self.get_players()
        player = players[player_id]
        
        return player['team']
    
    def get_team_attribute(self, player_id, attribute):
        team = self.get_team(player_id)
        return team.get(attribute)

    def get_team_name(self, player_id):
        return self.get_team_attribute(player_id, 'name')

    def get_team_id(self, player_id):
        return self.get_team_attribute(player_id, 'id')

    def get_team_badge(self, player_id, color='color'):
        if color not in ['color', 'gray', 'white']:
            self.logger.error('Invalid color. Please use "color", "gray" or "white"')
            color = 'color'  # use a default color
        return self.get_team_attribute(player_id, 'badge' + color.capitalize())
    
    def get_next_matchday(self, player_id):
        games_stats = self.get_games_stats()
        next_week_num = self.get_player_next_week_num(player_id)

        if not next_week_num:
            return None
        
        return games_stats[next_week_num-1]

    def get_playing_as_local(self, player_id): 
        team_id = self.get_team_id(player_id)
        matchday = self.get_next_matchday(player_id)
        return any(match['local']['id'] == team_id for match in matchday)
        
    def get_opponent(self, player_id):
        team_id = self.get_team_id(player_id)
        matchday = self.get_next_matchday(player_id)

        for match in matchday:
            if match['local']['id'] == team_id:
                return match['visitor']
            
            if match['visitor']['id'] == team_id:
                return match['local']
            
        return None
    
