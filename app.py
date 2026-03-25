from src.api.la_liga_api import LaLigaAPI
import streamlit as st
import random


# APIs
la_liga_api = LaLigaAPI()

# input - Select player by name
player_names = la_liga_api.get_players_names()
player_name = st.selectbox("Select Player", player_names)
player_id = la_liga_api.get_player_id(player_name)

# Get and display player image
player_image = la_liga_api.get_player_image()
if player_image:
    st.image(player_image)

# Get player stats and match info
la_liga_api.get_player_stats()
team_name, team_id, team_img = la_liga_api.get_team()
cum_points = la_liga_api.get_cum_points()
avg_points = la_liga_api.get_avg_points()
as_local = la_liga_api.get_as_local()
opponent_name, opponent_id, opponent_img = la_liga_api.get_opponent()

# Prediction: Use average points with some variance
if avg_points > 0:
    variance = random.uniform(0.8, 1.2)  # ±20% variance
    prediction = avg_points * variance
else:
    prediction = random.uniform(5, 10)  # Fallback if no data

st.write(f"**Predicted score for next match:** {prediction:.1f} points")
st.write(f"**Accumulated score:** {cum_points}")
st.write(f"**Average score:** {avg_points}")
st.markdown(f"**Next Opponent:** :blue[{opponent_name}]")
st.markdown(f'**Playing as local:** {":green[yes]" if as_local else ":red[no]"}')

# historical results
st.header(f"Historical Total Points")
df = la_liga_api.get_historical_total_points()
if not df.empty:
    st.bar_chart(df, x="week")
else:
    st.info("No historical data available")

# historical market value
st.header(f"Historical Market Value")
df = la_liga_api.get_historical_market_value()
if not df.empty:
    st.line_chart(df, x="date", y="marketValue")
else:
    st.info("No market value data available")
