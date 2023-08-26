import json
import sys
import os
import pandas as pd

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.api.la_liga_api import LaLigaAPI

# Get the PYTHONPATH environment variable
PROJECT_PATH = os.environ.get('PYTHONPATH', '')

# Function to load JSON data from a file
def load_json_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to update player data with their stats
def update_players_with_stats(players, player_stats):
    for player_id, player in players.items():
        if player['positionId'] == '5': # Skip coaches
            continue
        player['playerStats'] = player_stats[player_id]['playerStats']
    return players

# Function to fetch latest data from the API
def fetch_latest_data(api):
    players = api.get_players()
    games_stats = api.get_games_stats()
    return players, games_stats

# Function to process and merge player data
def process_and_merge_players(players_1, players_2, filename):
    # Convert player data to pandas dataframe
    players_1_df = pd.DataFrame.from_dict(players_1.values())
    players_1_df['id'] = players_1_df['id'].astype(int)
    players_1_df = players_1_df.set_index('id')

    players_2_df = pd.DataFrame.from_dict(players_2.values())
    players_2_df['id'] = players_2_df['id'].astype(int)
    players_2_df = players_2_df.set_index('id')
    
    # Merge player data from two different seasons
    players_merged_df = players_1_df.merge(players_2_df, on='id', how='outer', suffixes=('_1', ''))

    # Function to combine two lists
    def combine_lists(x, y):
        if isinstance(x, list) and isinstance(y, list):
            return x + y
        elif isinstance(x, list):
            return x
        elif isinstance(y, list):
            return y
        else:
            return None

    # Combine player stats from two different seasons
    players_merged_df['playerStats'] = players_merged_df.apply(lambda x: combine_lists(x['playerStats_1'], x['playerStats']), axis=1)
    players_merged_df = players_merged_df.drop(columns=[col for col in players_merged_df.columns if col.endswith('_1')])
    players_merged_df.to_parquet(f'../data/parquet/{filename}.parquet')

# Function to process and merge game stats
def process_and_merge_games_stats(games_stats_1, game_stats_2, filename):
    # Convert game stats to pandas dataframe
    games_stats_1_df = pd.DataFrame(games_stats_1).rename(columns=lambda x: 'match_' + str(x+1))
    games_stats_1_df['matchday'] = games_stats_1_df.index + 1

    games_stats_2_df = pd.DataFrame(game_stats_2).rename(columns=lambda x: 'match_' + str(x+1))
    games_stats_2_df['matchday'] = games_stats_2_df.index + 1
    
    # Merge game stats from two different seasons
    games_stats_df = pd.concat([games_stats_1_df, games_stats_2_df])
    games_stats_df.reset_index(drop=True, inplace=True)
    games_stats_df.to_parquet(PROJECT_PATH + f'/data/parquet/{filename}.parquet')

# Main function
def main():
    # Load data from JSON files
    players_22 = load_json_data(PROJECT_PATH + '/data/json/players.2022.json')
    player_stats_22 = load_json_data(PROJECT_PATH + '/data/json/players_stats.2022.json')
    games_stats_22 = load_json_data(PROJECT_PATH + '/data/json/games_stats.2022.json')

    # Update player data with their stats
    players_22 = update_players_with_stats(players_22, player_stats_22)
    
    # Fetch latest data from the API
    api = LaLigaAPI()
    players_23, games_stats_23 = fetch_latest_data(api)
    
    # Process and merge player and game stats
    process_and_merge_players(players_22, players_23, 'players_22_and_23')
    process_and_merge_games_stats(games_stats_22, games_stats_23, 'games_stats_22_and_23')

# Run the main function if the script is executed directly
if __name__ == "__main__":
    main()
