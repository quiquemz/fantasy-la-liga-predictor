import pandas as pd
import requests
import os
import json

class LaLigaAPI(object):

    # HTTP
    HTTPS = 'https://'
    DOMAIN = 'api.laligafantasymarca.com'

    # V1
    V1 = '/stats/v1'
    HTTPS_DOMAIN_V1 = f'{HTTPS}{DOMAIN}{V1}'
    ROUTE_WEEK = '/stats/week'

    # V3
    V3 = '/api/v3'
    HTTPS_DOMAIN_V3 = f'{HTTPS}{DOMAIN}{V3}'
    ROUTE_PLAYERS = '/players'

    # FILES
    PLAYERS_PATH = './data_json/players.json'
    PLAYER_PATH = './data_json/player'
    WEEK_STATS_PATH = './data_json/weeks_stats.json'

    def __init__(self) -> None:
        # get list of players ids from file
        self.players = None
        self.week_stats = None
        self.player_stats = None

        self.players = self.get_players()
        self.week_stats = self.get_week_stats()

    def get_players(self):
        # get from existing object
        if self.players:
            players = self.players

        # get from file
        elif os.path.isfile(self.PLAYERS_PATH):
            with open(self.PLAYERS_PATH) as f:
                players = json.load(f)

        # get from API
        else:
            response = requests.get(f'{self.HTTPS_DOMAIN_V3}{self.ROUTE_PLAYERS}')
            players = {p['nickname']: p for p in response.json()}
            
            with open(self.PLAYERS_PATH, 'w') as convert_file:
                convert_file.write(json.dumps(players))
        
        return players
    
    def get_week_stats(self):
        week_stats = []

        # get from existing object
        if self.week_stats:
            week_stats = self.week_stats

        # get from file
        elif os.path.isfile(self.WEEK_STATS_PATH):
            with open(self.WEEK_STATS_PATH) as f:
                week_stats = json.load(f)

        # get from API
        else:
            for w in range(38):
                response = requests.get(f'{self.HTTPS_DOMAIN_V3}{self.ROUTE_WEEK}')
                week_stats.append(response.json())

            with open(self.WEEK_STATS_PATH, 'w') as convert_file:
                convert_file.write(json.dumps(week_stats))
        
        return week_stats
    
    def get_players_names(self):
        return list(self.players.keys())
    
    def get_player_id(self, player):
        return self.players[player]['id']
    
    def get_player_image(self, player):
        return self.players[player]['images']['transparent']['256x256']

    def get_historical_market_value(self, player):
        player_id = self.players[player]['id']
        
        response = requests.get(f'{self.HTTPS_DOMAIN_V3}/player/{player_id}/market-value')
        player_hmv = response.json()
        player_hmv = [dict(p, **{'id': player_id}) for p in player_hmv]
        
        df = pd.json_normalize(player_hmv)
        df['date'] = pd.to_datetime(df['date'])

        return df
    
    def get_player_stats(self, player):
        player_id = self.players[player]['id']

        path = '_'.join([self.PLAYER_PATH, str(player_id)]) + '.json'
        
        # get from file (cache)
        if os.path.isfile(path):
            with open(path) as f:
                player_stats = json.load(f)

        # get from API
        else:
            response = requests.get(f'{self.HTTPS_DOMAIN_V3}/player/{player_id}')
            player_stats = response.json()
            
            with open(path, 'w') as convert_file:
                convert_file.write(json.dumps(player_stats))

        self.player_stats = player_stats

    def get_team(self):
        tname = self.player_stats['team']['name']
        tid = self.player_stats['team']['id']
        timg = self.player_stats['team']['badgeColor']
        return tname, tid, timg
    
    def get_cum_points(self):
        return sum([s['totalPoints'] for s in self.player_stats['playerStats']])
    
    def get_avg_points(self):
        stats = self.player_stats['playerStats']
        if len(stats) > 0:
            return sum([s['totalPoints'] for s in stats]) / len(stats)
        
        return 0
    
    def get_as_local(self, week_num):
        matchday = self.week_stats[week_num-1]
        team_id = int(self.get_team()[1])

        for match in matchday:
            if match['local']['id'] == team_id:
                return 1
            
            if match['visitor']['id'] == team_id:
                return 0
            
        return 0
    
    def get_opponent(self, week_num):
        matchday = self.week_stats[week_num-1]
        team_id = int(self.get_team()[1])

        for match in matchday:
            if match['local']['id'] == team_id:
                v = match['visitor']
                return v['name'], v['id'], v['badgeColor']
            
            if match['visitor']['id'] == team_id:
                l = match['local']
                return l['name'], l['id'], l['badgeColor']
            
        return None, 1, ''
    
    def get_historical_total_points(self):
        stats = self.player_stats['playerStats']
        data = [(i+1, s['totalPoints']) for i, s in enumerate(stats)]
        return pd.DataFrame(data, columns =['week', 'totalPoints'])