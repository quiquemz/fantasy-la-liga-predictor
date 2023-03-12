#!/usr/bin/env python
# coding: utf-8

# In[206]:


import requests
import json

import pandas as pd
import numpy as np


# # Data Frame

# In[207]:


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


# In[208]:


# get list of players ids
response = requests.get(f'{HTTPS_DOMAIN_V3}{ROUTE_PLAYERS}')

players = response.json()
players_ids = [p['id'] for p in players]

players_ids[:10]


# ## Player Stats

# In[209]:


player_stats_path = './data_json/player_stats.json'


# ### Get data from local JSON

# In[176]:


# with open(player_stats_path) as f:
#     players_stats = json.load(f)


# ### Get data from API

# In[210]:


# get player stats
print('Getting player stats...')

# get players stats info for each player
players_stats = []
for i, p_id in enumerate(players_ids):
    response = requests.get(f'{HTTPS_DOMAIN_V3}{ROUTE_PLAYER_STATS(p_id)}')
    p_stats = response.json()

    if p_stats['position'] != 'Entrenador':
        players_stats.append(p_stats)
    
    print(i+1, '- Retrieved player stats of id:', p_id)
    
# create file
with open(player_stats_path, 'w') as convert_file:
     convert_file.write(json.dumps(players_stats))

len(players_stats)


# ### Create data frame

# In[178]:


# # normalize player stats and create data frame
# df_players_stats = pd.json_normalize(players_stats, 
#                                         record_path=['playerStats'],
#                                         meta=['team', 'id', 'name', 'position'],
#                                         errors=None)

df_players_stats = pd.json_normalize(players_stats, 
                                        record_path=['playerStats'],
                                        meta=['team', 'id', 'name', 'position'],
                                        errors='raise')


# In[179]:


df_players_stats.shape


# ### Create column for each of the team information (teamName, teamId)

# In[180]:


# function to get team data
def flatten_team(d):
    return {'team_id': d['id'], 'team_shortName': d['shortName']}

# apply function to extract info
df_players_stats[['team_id', 'team_shortName']] = df_players_stats['team'].apply(lambda d: pd.Series(flatten_team(d)))

# drop team column
df_players_stats = df_players_stats.drop(columns='team')


# In[181]:


df_players_stats.head()


# ### Create column for each value in stats array (actual, points)

# In[182]:


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
    
df_players_stats.head()


# ### Average Points per Player

# In[183]:


# sort columns
df_players_stats = df_players_stats.sort_values(['id', 'weekNumber'])
df_players_stats.head()


# In[184]:


# columns we need from previous week
points_cols = [col for col in df_players_stats.columns if '_pts' in col]
actual_cols = [col for col in df_players_stats.columns if 'actual' in col]

# avg points colums names
# lm = "last match"
avg_points_cols = ['_'.join(['cumavg', col]) for col in points_cols]

df_players_stats['cum_totalPoints'] = df_players_stats.groupby('id')['totalPoints'].apply(lambda x: x.shift(1).cumsum())

# add cumulative average points
df_players_stats['cumavg_totalPoints'] = df_players_stats.groupby('id')['totalPoints'].apply(lambda x: x.shift(1).expanding().mean())

# dropping points of current week
df_players_stats = df_players_stats.drop(columns=(points_cols + actual_cols))



# In[187]:


df_players_stats['cum_totalPoints'] = df_players_stats['cum_totalPoints'].fillna(0)
df_players_stats['cumavg_totalPoints'] = df_players_stats['cumavg_totalPoints'].fillna(0)

df_players_stats.head()


# In[188]:


df_players_stats[['id', 'cumavg_totalPoints']].head()


# ## Week Info

# In[189]:


weeks_stats_path = './data_json/weeks_stats.json'


# ### Get data from local JSON

# In[190]:


# with open(weeks_stats_path) as f:
#     weeks_stats = json.load(f)


# ### Get data from API

# In[191]:


# get games stats per week
print("Getting week stas...")

weeks = list(range(1, 39))
weeks_stats = []
for w in weeks:
    response = requests.get(f'{HTTPS_DOMAIN_V1}{ROUTE_WEEK(w)}')
    weeks_stats.append(response.json())

    print(w, '- Retrieved week stats for week:', w)
    
# create file 
with open(weeks_stats_path, 'w') as convert_file:
     convert_file.write(json.dumps(weeks_stats))


# ### Create data frame

# In[192]:


# create a flattened list of the week stats
flat_weeks_stats = [
    {'weekNumber': i+1, **item}
    for i, sublist in enumerate(weeks_stats)
        for item in sublist
]


# In[193]:


# convert json to data frame
df_weeks_stats = pd.json_normalize(flat_weeks_stats)

df_weeks_stats = df_weeks_stats[['weekNumber',
                                 'localScore', 
                                 'local.id', 
                                 'local.shortName', 
                                 'visitorScore', 
                                 'visitor.id', 
                                 'visitor.shortName']]


# In[194]:


df_weeks_stats.head()


# ## Merge Week Info with Player Stats to add Match Features

# In[195]:


# convert to string
df_weeks_stats['local.id'] = df_weeks_stats['local.id'].astype(str)
df_weeks_stats['visitor.id'] = df_weeks_stats['visitor.id'].astype(str)


# ### Adding next match features

# In[196]:


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

df.head()


# In[197]:


# adding next match features

# feature describing if played as local
df['curr_match_as_local'] = ~df['localScore_l'].isna()

# feature describing last match opponent
df['curr_match_opponent_id'] = np.where(
    df['curr_match_as_local'], # if
    df['visitor.id_l'], # then
    df['local.id_v'])   # else

df.head()


# In[198]:


# define condition of redundant columns
reduntant_cols_cond = lambda c: c.startswith("local") or c.startswith("visitor") or c.startswith("lastWeekNumber")

# select redundant columns
redundant_cols = [col for col in df.columns if reduntant_cols_cond(col)]

# drop redundant columns
df = df.drop(columns=redundant_cols)

df.head()

# save new dataset
df.to_csv('./data_csv/players_full_data_v2.csv', index=False)

# ### Adding Last Match Features

# In[199]:


# # add last week number to join
# df['lastWeekNumber'] = df.groupby(['id'])['weekNumber'].shift(1)

# df.head()


# In[200]:


# # rename column to avoid conflict
# df = df.rename(columns={'weekNumber': 'week'})

# # merge based on local team id
# df = df_weeks_stats.merge(
#         df, 
#         how='right',
#         right_on=['team_shortName', 'lastWeekNumber'],
#         left_on=['local.shortName', 'weekNumber'])

# # merge based on visitor team id
# df = df_weeks_stats.merge(
#         df.drop(columns='weekNumber'),
#         how='right',
#         right_on=['team_shortName', 'lastWeekNumber'],
#         left_on=['visitor.shortName', 'weekNumber'],
#         suffixes=('_v', '_l')) # visitor, local

# # drop week number as it is irrelevant
# df = df.drop(columns='weekNumber')


# In[201]:


# # adding last match features

# # feature describing if played as local
# df['last_match_as_local'] = ~df['localScore_l'].isna()

# # feature describing last match opponent
# df['last_match_opponent_id'] = np.where(df['last_match_as_local'], df['visitor.id_l'], df['local.id_v'])

# # feature describing last match goals
# df['last_match_goals'] = np.where(df['last_match_as_local'], df['localScore_l'], df['visitorScore_v'])

# # feature describing last match oponent goals
# df['last_match_oponent_goals'] = np.where(df['last_match_as_local'], df['visitorScore_l'], df['localScore_v'])

# # feature describing if game status
# match_result_conditions = [
#     df['last_match_goals'].isna(),
#     df['last_match_goals'] > df['last_match_oponent_goals'],
#     df['last_match_goals'] < df['last_match_oponent_goals'],
#     df['last_match_goals'] == df['last_match_oponent_goals']
# ]
# match_result_values = [np.nan, 'win', 'loose', 'draw']
# df['last_match_status'] = np.select(match_result_conditions, match_result_values)

# df.head(10)


# In[202]:


# # define condition of columns we want to drop
# reduntant_cols_cond = (lambda c: c.startswith("local") or 
#                                  c.startswith("visitor") or 
#                                  c.startswith("lastWeekNumber"))

# # select columns we want to drop
# redundant_cols = [col for col in df.columns if reduntant_cols_cond(col)]

# # drop columns
# df = df.drop(columns=redundant_cols)

# df.head()


# In[203]:


# df.shape


# In[204]:


# drop the 


# In[205]:


# ## Historical Market Values

# ### Get data from JSON

# In[13]:


# historical_market_values_path_json = './data_json/historical_market_values.json'
# historical_market_values_path_csv = './data_csv/historical_market_values.csv'


# In[4]:


# with open(historical_market_values_path_json) as f:
#     historical_market_values = json.load(f)


# ### Get data from API

# In[ ]:


# # get historical market value per player
# print('Getting players historical values')

# # get hmv for each player
# historical_market_values = []
# for i, p_id in enumerate(players_ids):
#     response = requests.get(f'{HTTPS_DOMAIN_V3}{ROUTE_MARKET_VALUE(p_id)}')
#     player_hmv = response.json()
#     player_hmv = [dict(p, **{'id': p_id}) for p in player_hmv]

#     historical_market_values += player_hmv

#     print(i+1, '- Retrieved historical market value of id:', p_id)

# # create file
# with open(historical_market_values_path, 'w') as convert_file:
#      convert_file.write(json.dumps(historical_market_values))

# len(historical_market_values)


# In[12]:


# df_market_values = pd.json_normalize(historical_market_values)


# In[6]:


# df_market_values.shape


# In[7]:


# df_market_values.head()


# In[172]:


# df_market_values.to_csv(historical_market_values_path_csv, index=False)

