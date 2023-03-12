import requests
import os

class LaLigaPredictor():

    HTTPS = 'https://'
    DOMAIN = os.environ['PREDICTOR_DOMAIN'] + '/prod'
    
    ROUTE_PREDICT = '/predict-points'

    def __init__(self) -> None:
        pass

    def get_prediction(self, id, team_id, cum_totalPoints, cumavg_totalPoints, curr_match_as_local, curr_match_opponent_id):
        
        params = '?' + '&'.join([
            f'id={id}', 
            f'team_id={team_id}', 
            f'cum_totalPoints={cum_totalPoints}', 
            f'cumavg_totalPoints={cumavg_totalPoints}', 
            f'curr_match_as_local={curr_match_as_local}', 
            f'curr_match_opponent_id={curr_match_opponent_id}'])
        
        response = requests.get(f'{self.HTTPS}{self.DOMAIN}{self.ROUTE_PREDICT}{params}')

        return response.json()
        

        

