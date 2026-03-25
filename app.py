import streamlit as st
import random
from datetime import datetime
from src.api.la_liga_api import LaLigaAPI

# Configure page
st.set_page_config(
    page_title="La Liga Fantasy Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .opponent-badge {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# Initialize session state and cache
@st.cache_resource
def init_api():
    """Initialize LaLigaAPI (cached to avoid reloading)."""
    return LaLigaAPI()


api = init_api()

api = init_api()

# Sidebar for player selection
st.sidebar.title("⚽ Player Selection")

# Cache player names in session state
if "player_names_cache" not in st.session_state:
    st.session_state.player_names_cache = api.get_players_names()
    st.session_state.selected_player_name = None
    st.session_state.selected_player_id = None

player_names = st.session_state.player_names_cache

# Search box
search_query = st.sidebar.text_input(
    "🔍 Search players", 
    placeholder="Type name, e.g., 'Bellingham'",
    label_visibility="collapsed"
)

# Filter players based on search query
if search_query:
    filtered_players = [
        name for name in player_names 
        if search_query.lower() in name.lower()
    ]
else:
    filtered_players = player_names[:20]  # Show first 20 by default
    show_all = st.sidebar.checkbox("Show all 957 players", value=False)
    if show_all:
        filtered_players = player_names

# Display search results
if filtered_players:
    if search_query:
        st.sidebar.caption(f"Found {len(filtered_players)} player{'s' if len(filtered_players) != 1 else ''}")
    
    player_name = st.sidebar.radio(
        "Select a Player",
        filtered_players,
        label_visibility="collapsed"
    )
    
    # Only update if selection changed
    if player_name != st.session_state.selected_player_name:
        st.session_state.selected_player_name = player_name
        st.session_state.selected_player_id = api.get_player_id(player_name)
    
    player_id = st.session_state.selected_player_id
else:
    st.sidebar.warning("No players found matching your search.")
    player_name = None
    player_id = None




# Main header
st.title("🔮 La Liga Fantasy Predictor")
st.markdown("---")

if player_id and player_name:
    # Top row: Player image and basic info
    col1, col2 = st.columns([1, 2])

    with col1:
        player_image = api.get_player_image()
        if player_image:
            st.image(player_image, use_container_width=True)
        else:
            st.info("Player image not available")

    with col2:
        api.get_player_stats()
        team_name, team_id, team_img = api.get_team()
        cum_points = api.get_cum_points()
        avg_points = api.get_avg_points()
        as_local = api.get_as_local()
        opponent_name, opponent_id, opponent_img = api.get_opponent()
        match_date, match_time = api.get_match_date_formatted()
        match_week = api.get_match_week_number()

        # Player name
        st.markdown(f"## {player_name}")

        # Team name and badge inline
        if team_img:
            try:
                st.markdown(
                    f"<div style='display: flex; align-items: center; gap: 10px;'><span style='font-size: 16px;'><b>Team:</b> {team_name}</span><img src='{team_img}' width='40' style='vertical-align: middle;'></div>",
                    unsafe_allow_html=True,
                )
            except:
                st.markdown(f"**Team:** {team_name}")
        else:
            st.markdown(f"**Team:** {team_name}")

        st.markdown("---")

        # Metrics row with better spacing
        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Total Points", int(cum_points))
        with metric_cols[1]:
            st.metric("Avg/Match", f"{avg_points:.1f}")
        with metric_cols[2]:
            st.metric("Playing as", "🏠 Home" if as_local else "✈️ Away")
        with metric_cols[3]:
            st.metric("Week", match_week)

    st.markdown("---")

    # Tabs for organized display
    tab1, tab2, tab3 = st.tabs(["📋 Next Match", "📊 Statistics", "📈 History"])

    with tab1:
        st.subheader("Next Fixture")

        # Opponent information first
        if opponent_img:
            try:
                st.markdown(
                    f"<div style='display: flex; align-items: center; gap: 15px;'><span style='font-size: 16px;'><b>Opponent:</b> {opponent_name}</span><img src='{opponent_img}' width='50' style='vertical-align: middle;'></div>",
                    unsafe_allow_html=True,
                )
            except:
                st.markdown(f"**Opponent:** {opponent_name}")
        else:
            st.markdown(f"**Opponent:** {opponent_name}")

        # Match details row
        match_info_cols = st.columns(3)

        with match_info_cols[0]:
            st.write(f"**Date:** {match_date}")
        with match_info_cols[1]:
            st.write(f"**Time:** {match_time} (Spain)")
        with match_info_cols[2]:
            st.write(f"**Week:** {match_week}")

    with tab2:
        st.subheader("Player Performance")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Performance Metrics")

            # Prediction: Use average points with variance
            if avg_points > 0:
                variance = random.uniform(0.85, 1.15)  # ±15% variance
                prediction = avg_points * variance
            else:
                prediction = random.uniform(5, 10)

            confidence = "High" if avg_points > 7 else "Medium" if avg_points > 4 else "Low"

            st.markdown(
                f"""
            - **Total Points:** {cum_points}
            - **Average Points/Match:** {avg_points:.2f}
            - **Prediction for Next Match:** {prediction:.1f} pts
            - **Confidence:** {confidence}
            """
            )

        with col2:
            st.markdown("### Match Factor Analysis")
            if as_local:
                st.success("🏠 Home Advantage")
                st.markdown("Players typically perform **better** at home")
            else:
                st.warning("✈️ Away Match")
                st.markdown("Some players perform **worse** away from home")

            st.markdown("---")
            st.markdown(f"**Next Opponent:** {opponent_name}")

    with tab3:
        st.subheader("Historical Data")

        hist_col1, hist_col2 = st.columns(2)

        with hist_col1:
            st.markdown("### Points by Week")
            df = api.get_historical_total_points()
            if not df.empty:
                st.bar_chart(df.set_index("week"))
            else:
                st.info("No historical data available")

        with hist_col2:
            st.markdown("### Market Value Trend")
            df = api.get_historical_market_value()
            if not df.empty:
                df["date"] = df["date"].str[:10]  # Extract date only
                st.line_chart(df.set_index("date"))
            else:
                st.info("No market value data available")

    st.markdown("---")
    st.markdown("_Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "_")

else:
    st.info("👈 Select a player from the sidebar to get started. Use the search box to find players quickly!")
