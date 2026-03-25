import os
import json
import pytz
import pandas as pd

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils.api_manager import APIManager
from src.utils.cache_manager import CacheManager
from src.utils.decorators import load_and_cache, update_and_cache

from src.config import SEASON, WEEKS_TOTAL


class LaLigaAPI(object):

    # HTTP
    HTTPS = os.getenv("HTTPS", "https://")
    DOMAIN = os.getenv("DOMAIN", "api-fantasy.llt-services.com")

    # V1
    V1 = os.getenv("V1", "/stats/v1")
    HTTPS_DOMAIN_V1 = f"{HTTPS}{DOMAIN}{V1}"
    ROUTE_WEEK = os.getenv("ROUTE_WEEK", "/stats/week")

    # V3
    V3 = os.getenv("V3", "/api/v3")
    HTTPS_DOMAIN_V3 = f"{HTTPS}{DOMAIN}{V3}"
    ROUTE_PLAYERS = os.getenv("ROUTE_PLAYERS", "/players")

    # FILES
    # Get the parent directory of the current file
    PARENT_DIR = os.getenv(
        "PARENT_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/json"),
    )
    PLAYERS_PATH = f"players.{SEASON}.json"
    ALL_WEEKS_FIXTURES_PATH = f"all_weeks_fixtures.{SEASON}.json"

    # Spain Timezon
    TZ_SPAIN = pytz.timezone("Europe/Madrid")

    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = self.PARENT_DIR

        self.api_v1 = APIManager(self.HTTPS_DOMAIN_V1)
        self.api_v3 = APIManager(self.HTTPS_DOMAIN_V3)
        self.cache_manager = CacheManager(cache_dir)
        self.current_player_id = None
        self._players_cache = None
        self._player_stats_cache = {}

    @load_and_cache()
    def get_players(
        self, force_refresh=False
    ):  # "force_refresh" is used in the decorator
        player_ids = self._load_cached_player_ids()
        players = {}

        # Use concurrent requests to fetch player data in parallel
        def fetch_player(p_id):
            try:
                player_data = self.api_v3.request(f"/player/{p_id}")
                return str(p_id), player_data
            except Exception as e:
                print(f"Error fetching player {p_id}: {e}")
                return None

        # Fetch with 20 concurrent workers
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_player, p_id): p_id for p_id in player_ids}
            completed = 0

            for future in as_completed(futures):
                result = future.result()
                if result:
                    p_id, player_data = result
                    players[p_id] = player_data

                completed += 1
                if completed % 50 == 0:
                    print(
                        f"Fetched player data for {completed}/{len(player_ids)} players"
                    )

        print(f"Successfully fetched data for {len(players)} players")
        return players

    def _load_cached_player_ids(self):
        """Load cached player IDs from discovery cache."""
        # Try notebooks cache first, then fall back to src cache
        cache_paths = [
            "./notebooks/data_json/valid_player_ids_cache.json",
            os.path.join(self.cache_manager.cache_dir, "valid_player_ids_cache.json"),
        ]

        for cache_path in cache_paths:
            if os.path.exists(cache_path):
                try:
                    with open(cache_path) as f:
                        player_ids = json.load(f)
                    print(
                        f"Loaded {len(player_ids)} cached player IDs from {cache_path}"
                    )
                    return player_ids
                except Exception as e:
                    print(f"Error reading cache from {cache_path}: {e}")

        raise FileNotFoundError(
            f"Player IDs cache not found. Please run the player discovery in the notebook first. "
            f"Expected cache at: {cache_paths[0]}"
        )

    @load_and_cache()
    def get_all_weeks_fixtures(self, force_refresh=False):
        """Fetch all week fixtures (1-38) in parallel and return as flat list.
        Includes historical matches with scores and future matches without scores."""
        try:
            print(f"Fetching fixtures for weeks 1-{WEEKS_TOTAL}...")
            all_matches = []

            def fetch_week(week_num):
                try:
                    matches = self.api_v1.request(f"{self.ROUTE_WEEK}/{week_num}")
                    if isinstance(matches, list):
                        # Ensure all matches have a week number
                        for match in matches:
                            if isinstance(match, dict):
                                match["weekNumber"] = week_num
                        return matches
                    return []
                except Exception as e:
                    print(f"Error fetching week {week_num}: {e}")
                    return []

            # Fetch all weeks in parallel
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {
                    executor.submit(fetch_week, w): w for w in range(1, WEEKS_TOTAL + 1)
                }
                completed = 0

                for future in as_completed(futures):
                    week_matches = future.result()
                    all_matches.extend(week_matches)
                    completed += 1
                    if completed % 10 == 0:
                        print(f"Fetched {completed}/{WEEKS_TOTAL} weeks")

            print(
                f"Successfully fetched {len(all_matches)} total matches from all weeks"
            )
            return all_matches

        except Exception as e:
            print(f"Error fetching all weeks: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_next_match_for_team(self, team_id):
        """Find the next upcoming match for the given team from all weeks.
        Returns the match dict or None if not found."""
        try:
            # Fetch all weeks fixtures (cached)
            all_matches = self.get_all_weeks_fixtures()

            if not all_matches:
                print("No matches available")
                return None

            # Ensure team_id is an integer for comparison
            team_id = int(team_id) if team_id else None
            print(f"Searching for team {team_id} across {len(all_matches)} matches")

            # Debug: collect all team IDs
            all_team_ids = set()
            for match in all_matches:
                if isinstance(match, dict):
                    local_id = match.get("local", {}).get("id")
                    visitor_id = match.get("visitor", {}).get("id")
                    if local_id:
                        all_team_ids.add(local_id)
                    if visitor_id:
                        all_team_ids.add(visitor_id)

            print(f"Available team IDs: {sorted(all_team_ids)}")
            print(f"Team {team_id} is in list: {team_id in all_team_ids}")

            # Find first match for this team (next matchday)
            for match in all_matches:
                if not isinstance(match, dict):
                    continue

                local_id = match.get("local", {}).get("id")
                visitor_id = match.get("visitor", {}).get("id")

                # Skip matches that already have scores (past matches)
                if (
                    match.get("localScore") is not None
                    or match.get("visitorScore") is not None
                ):
                    continue

                if local_id == team_id or visitor_id == team_id:
                    local_name = match.get("local", {}).get("mainName", "Unknown")
                    visitor_name = match.get("visitor", {}).get("mainName", "Unknown")
                    week_num = match.get("weekNumber", "?")
                    print(
                        f"Found next match for team {team_id} in week {week_num}: {local_name} vs {visitor_name}"
                    )
                    return match

            print(f"No upcoming match found for team {team_id}")
            return None

        except Exception as e:
            print(f"Error fetching match for team {team_id}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def get_match_date_formatted(self):
        """Get formatted date and time for next match."""
        if not self.current_player_id:
            return "N/A", "N/A"

        team_id = int(self.get_team()[1]) if self.get_team()[1] else None
        match = self.get_next_match_for_team(team_id)

        if not match:
            return "N/A", "N/A"

        try:
            date_str = match.get("date", "")
            if date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                # Convert to Spain timezone
                dt_spain = dt.astimezone(self.TZ_SPAIN)
                date_formatted = dt_spain.strftime("%a, %d %b")
                time_formatted = dt_spain.strftime("%H:%M")
                return date_formatted, time_formatted
        except Exception as e:
            print(f"Error formatting match date: {e}")

        return "N/A", "N/A"

    def get_match_week_number(self):
        """Get week number of next match."""
        if not self.current_player_id:
            return "N/A"

        team_id = int(self.get_team()[1]) if self.get_team()[1] else None
        match = self.get_next_match_for_team(team_id)

        if not match:
            return "N/A"

        return match.get("weekNumber", "N/A")

    # ============== APP-FRIENDLY METHODS ==============

    def get_players_names(self):
        """Get list of all player names sorted alphabetically."""
        players = self.get_players()
        names = [p.get("name", f"Player {p_id}") for p_id, p in players.items()]
        return sorted(names)

    def get_player_id(self, player_name):
        """Get player ID by player name."""
        players = self.get_players()
        for p_id, p in players.items():
            if p.get("name") == player_name:
                self.current_player_id = str(p_id)
                return str(p_id)
        return None

    def _get_current_player(self):
        """Get current player data."""
        if not self.current_player_id:
            raise ValueError("No player selected. Call get_player_id() first.")
        players = self.get_players()
        return players.get(self.current_player_id)

    def get_player_image(self, player_name=None):
        """Get player image by name or current player."""
        if player_name:
            player_id = self.get_player_id(player_name)
        else:
            player_id = self.current_player_id

        if not player_id:
            raise ValueError("No player specified or selected.")

        players = self.get_players()
        player = players.get(player_id, {})

        try:
            return player["images"]["transparent"]["256x256"]
        except (KeyError, TypeError):
            return None

    def get_player_stats(self, player_name=None):
        """Get/update player stats and set as current player."""
        if player_name:
            self.get_player_id(player_name)

        if not self.current_player_id:
            raise ValueError("No player selected.")

        # Cache stats for current player
        if self.current_player_id not in self._player_stats_cache:
            try:
                stats = self.api_v3.request(f"/player/{self.current_player_id}")
                self._player_stats_cache[self.current_player_id] = stats
            except Exception as e:
                print(f"Error fetching player stats: {e}")
                return None

        return self._player_stats_cache.get(self.current_player_id)

    def get_team(self):
        """Get current player's team info as tuple (name, team_id, badge_image)."""
        player = self._get_current_player()
        team = player.get("team", {})

        team_name = team.get("name", "Unknown")
        team_id = team.get("id", None)

        # Try to get badge from player data first, then from matches
        badge_img = team.get("badgecolor", "") or team.get("badgeColor", "")

        # If no badge in player data, try to get it from the match data
        if not badge_img and team_id:
            try:
                match = self.get_next_match_for_team(team_id)
                if match:
                    local_id = match.get("local", {}).get("id")
                    if local_id == team_id:
                        badge_img = match.get("local", {}).get("badgeColor", "")
                    else:
                        visitor_id = match.get("visitor", {}).get("id")
                        if visitor_id == team_id:
                            badge_img = match.get("visitor", {}).get("badgeColor", "")
            except:
                pass

        return team_name, team_id, badge_img

    def get_cum_points(self):
        """Get cumulative total points for current player from actual stats."""
        try:
            stats = self.get_player_stats()
            if not stats or "playerStats" not in stats:
                return 0

            player_stats = stats.get("playerStats", [])
            total_points = sum(ps.get("totalPoints", 0) for ps in player_stats)
            return total_points
        except Exception as e:
            print(f"Error calculating cumulative points: {e}")
            return 0

    def get_avg_points(self):
        """Get average points per match for current player from actual stats."""
        try:
            stats = self.get_player_stats()
            if not stats or "playerStats" not in stats:
                return 0

            player_stats = stats.get("playerStats", [])
            if not player_stats:
                return 0

            total_points = sum(ps.get("totalPoints", 0) for ps in player_stats)
            avg_points = total_points / len(player_stats)
            return round(avg_points, 2)
        except Exception as e:
            print(f"Error calculating average points: {e}")
            return 0

    def get_as_local(self):
        """Get if current player is playing as local in next match."""
        if not self.current_player_id:
            raise ValueError("No player selected.")

        team_id = int(self.get_team()[1]) if self.get_team()[1] else None
        match = self.get_next_match_for_team(team_id)

        if not match:
            print(f"No next match found for team {team_id}")
            return False

        # Check if team is playing as local
        local_id = match.get("local", {}).get("id")
        return local_id == team_id

    def get_opponent(self):
        """Get opponent info for current player's next match as tuple (name, opponent_id, badge_image)."""
        if not self.current_player_id:
            raise ValueError("No player selected.")

        team_id = int(self.get_team()[1]) if self.get_team()[1] else None
        match = self.get_next_match_for_team(team_id)

        if not match:
            print(f"No next match found for team {team_id}")
            return "Unknown", None, ""

        # Determine if playing as local or visitor, and get opponent
        local_id = match.get("local", {}).get("id")
        visitor_id = match.get("visitor", {}).get("id")

        if local_id == team_id:
            opponent = match.get("visitor", {})
        elif visitor_id == team_id:
            opponent = match.get("local", {})
        else:
            print(f"Team {team_id} not found in match")
            return "Unknown", None, ""

        opponent_name = opponent.get("mainName", "Unknown")
        opponent_id = opponent.get("id", None)
        badge_img = opponent.get("badgeColor", "")  # This is a URL now

        return opponent_name, opponent_id, badge_img

    def get_historical_total_points(self):
        """Get historical total points for current player as DataFrame."""
        try:
            stats = self.get_player_stats()
            if not stats or "playerStats" not in stats:
                return pd.DataFrame({"week": [], "points": []})

            player_stats = stats.get("playerStats", [])
            data = {
                "week": [
                    ps.get("weekNumber", i + 1) for i, ps in enumerate(player_stats)
                ],
                "points": [ps.get("totalPoints", 0) for ps in player_stats],
            }
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error fetching historical points: {e}")
            return pd.DataFrame({"week": [], "points": []})

    def get_historical_market_value(self, player_name=None):
        """Get historical market value for player as DataFrame."""
        try:
            if player_name:
                player_id = self.get_player_id(player_name)
            else:
                player_id = self.current_player_id

            if not player_id:
                raise ValueError("No player specified or selected.")

            # Fetch market value history from API
            print(f"Fetching market value for player {player_id}")
            market_values = self.api_v3.request(f"/player/{player_id}/market-value")

            if not market_values:
                print("No market values returned")
                return pd.DataFrame({"date": [], "marketValue": []})

            # Handle both list and dict responses
            if isinstance(market_values, dict):
                market_values = market_values.get(
                    "historicalMarketValues", market_values.get("data", [])
                )

            if not market_values:
                return pd.DataFrame({"date": [], "marketValue": []})

            data = {
                "date": [mv.get("date", "") for mv in market_values],
                "marketValue": [mv.get("marketValue", 0) for mv in market_values],
            }
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            import traceback

            print(f"Error fetching historical market value: {e}")
            traceback.print_exc()
            return pd.DataFrame({"date": [], "marketValue": []})
