from src.apis.la_liga_api import LaLigaAPI
from predictor import LaLigaPredictor
import streamlit as st


# APIs
la_liga_api = LaLigaAPI()
predictor = LaLigaPredictor()

# input
player = st.selectbox('Select Player', la_liga_api.get_players_names())
player_id = la_liga_api.get_player_id(player)

player_image = la_liga_api.get_player_image(player)
st.image(player_image)

# next match results
# parameters for prediction
la_liga_api.get_player_stats(player)
team, team_id, team_img = la_liga_api.get_team()
cum_points = la_liga_api.get_cum_points()
avg_points = la_liga_api.get_avg_points()
as_local = la_liga_api.get_as_local()
opponent, opponent_id, opponent_img = la_liga_api.get_opponent()

# prediction
prediction = predictor.get_prediction(player_id, team_id, cum_points, avg_points, as_local, opponent_id)
st.write('Predicted score for next match', prediction)
st.write('Accumulated score', cum_points)
st.write('Average score', avg_points)
st.markdown(f'Next Opponent: :blue[{opponent}]')
# st.image([team_img, opponent_img])
st.markdown(f'Playing as local {":green[yes]" if as_local else ":red[no]"}')

# historical results
st.header(f'Historical Total Points')
df = la_liga_api.get_historical_total_points()
st.bar_chart(df, x='week')

# historical market value
st.header(f'Historical Market Value')
df = la_liga_api.get_historical_market_value(player)
st.line_chart(df, x='date', y='marketValue')

