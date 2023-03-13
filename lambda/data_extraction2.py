import requests
import json
import pandas as pd
import numpy as np
import boto3

from io import StringIO 


# Constants
HTTPS = 'https://'
DOMAIN = 'api.laligafantasymarca.com'

# V1
V1 = '/stats/v1'
HTTPS_DOMAIN_V1 = f'{HTTPS}{DOMAIN}{V1}'
ROUTE_WEEK = lambda week: f'/stats/week/{week}'

# V3
V3 = '/api/v3'
HTTPS_DOMAIN_V3 = f'{HTTPS}{DOMAIN}{V3}'
ROUTE_PLAYERS = '/players'
ROUTE_MARKET_VALUE = lambda id: f'/player/{id}/market-value'
ROUTE_PLAYER_STATS = lambda id: f'/player/{id}'

# get list of players ids
def get_list_players_ids():
    response = requests.get(f'{HTTPS_DOMAIN_V3}{ROUTE_PLAYERS}')

    players = response.json()
    players_ids = [p['id'] for p in players]

    return players_ids

# get players stats info for each player
def get_player_stats(players_ids):
    print('Getting player stats...')
    
    players_stats = []
    for i, p_id in enumerate(players_ids):
        response = requests.get(f'{HTTPS_DOMAIN_V3}{ROUTE_PLAYER_STATS(p_id)}')
        p_stats = response.json()

        if p_stats['position'] != 'Entrenador':
            players_stats.append(p_stats)
    
        print(i+1, '- Retrieved player stats of id:', p_id)
    
    # TODO wite file to s3 bucket
    
    
    return players_stats

# get players stats df
def get_players_stats_df(players_stats):

    # function to get team data
    def flatten_team(d):
        return {'team_id': d['id'], 'team_shortName': d['shortName']}

    # normalize json
    df_players_stats = pd.json_normalize(players_stats, 
                                        record_path=['playerStats'],
                                        meta=['team', 'id', 'name', 'position'],
                                        errors='raise')



    # apply function to extract info
    df_players_stats[['team_id', 'team_shortName']] = df_players_stats['team'].apply(lambda d: pd.Series(flatten_team(d)))

    # drop team column
    df_players_stats = df_players_stats.drop(columns='team')

    # create new column names based on the original
    stats_new_info = []
    for col in df_players_stats.columns:
        if "stats." not in col:
            continue
    
        stats_new_info.append({
        "current_name": col,
        "new_name_actual": col.replace("stats.", "") + "_actual",
        "new_name_points": col.replace("stats.", "") + "_pts",
    })

    # add information to new columns and drop original
    for sni in stats_new_info:
        curr_col = sni['current_name']
        new_col1 = sni['new_name_actual']
        new_col2 = sni['new_name_points']

        df_players_stats[[new_col1, new_col2]] = pd.DataFrame(df_players_stats[curr_col].to_list())
        df_players_stats = df_players_stats.drop(columns=curr_col)

    # sort columns
    df_players_stats = df_players_stats.sort_values(['id', 'weekNumber'])
    df_players_stats.head()

    # columns we need from previous week
    points_cols = [col for col in df_players_stats.columns if '_pts' in col]
    actual_cols = [col for col in df_players_stats.columns if 'actual' in col]

    # add cumulative points
    df_players_stats['cum_totalPoints'] = df_players_stats.groupby('id')['totalPoints'].apply(lambda x: x.shift(1).cumsum())

    # add cumulative average points
    df_players_stats['cumavg_totalPoints'] = df_players_stats.groupby('id')['totalPoints'].apply(lambda x: x.shift(1).expanding().mean())

    # dropping points of current week
    df_players_stats = df_players_stats.drop(columns=(points_cols + actual_cols))
    df_players_stats['cum_totalPoints'] = df_players_stats['cum_totalPoints'].fillna(0)
    df_players_stats['cumavg_totalPoints'] = df_players_stats['cumavg_totalPoints'].fillna(0)
    
    return df_players_stats

# merge week information with players
def merge_weeks_and_players(df_players_stats, df_weeks_stats):
    # convert to string
    df_weeks_stats['local.id'] = df_weeks_stats['local.id'].astype(str)
    df_weeks_stats['visitor.id'] = df_weeks_stats['visitor.id'].astype(str)

    # ### Adding next match features
    # merge based on local team id
    df = df_weeks_stats.merge(
        df_players_stats, 
        how='right',
        right_on=['team_id', 'weekNumber'],
        left_on=['local.id', 'weekNumber'])

    # merge based on visitor team id
    df = df_weeks_stats.merge(
        df,
        how='right',
        right_on=['team_id', 'weekNumber'],
        left_on=['visitor.id', 'weekNumber'],
        suffixes=('_v', '_l')) # visitor, local

    # adding next match features
    # feature describing if played as local
    df['curr_match_as_local'] = ~df['localScore_l'].isna()

    # feature describing last match opponent
    df['curr_match_opponent_id'] = np.where(
    df['curr_match_as_local'], # if
    df['visitor.id_l'], # then
    df['local.id_v'])   # else

    # define condition of redundant columns
    reduntant_cols_cond = lambda c: c.startswith("local") or c.startswith("visitor") or c.startswith("lastWeekNumber")

    # select redundant columns
    redundant_cols = [col for col in df.columns if reduntant_cols_cond(col)]

    # drop redundant columns
    df = df.drop(columns=redundant_cols)
    return df

# get week stats
def get_week_stats_df():
    weeks = list(range(1, 39))
    weeks_stats = []
    for w in weeks:
        response = requests.get(f'{HTTPS_DOMAIN_V1}{ROUTE_WEEK(w)}')
        weeks_stats.append(response.json())

        print(w, '- Retrieved week stats for week:', w)

    # create a flattened list of the week stats
    flat_weeks_stats = [
        {'weekNumber': i+1, **item}
        for i, sublist in enumerate(weeks_stats)
            for item in sublist
    ]


    # convert json to data frame
    df_weeks_stats = pd.json_normalize(flat_weeks_stats)

    df_weeks_stats = df_weeks_stats[['weekNumber',
                                 'localScore', 
                                 'local.id', 
                                 'local.shortName', 
                                 'visitorScore', 
                                 'visitor.id', 
                                 'visitor.shortName']]
                                     
    return df_weeks_stats

# lambda function
def lambda_handler(event, context):
    players_ids = get_list_players_ids()
    players_stats = get_player_stats(players_ids)
    df_players_stats = get_players_stats_df(players_stats)
    
    df_weeks_stats = get_week_stats_df()
    
    df = merge_weeks_and_players(df_players_stats, df_weeks_stats)
    
    # save new dataset
    bucket = 'la-liga-final-project' # already created on S3
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3_resource = boto3.resource('s3')
    s3_resource.Object(bucket, 'datasets/players_full_data_v2.csv').put(Body=csv_buffer.getvalue())
    
    return 'Success'
    