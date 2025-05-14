import time
from omniORB import CORBA
import GameIDL
from common import current_time, console_lock
from session import SessionManager
from player import PlayerAccount

class LeaderboardManager:
    def __init__(self, game_service, player):
        self.game_service = game_service
        self.player = player

    def get_leaderboard_data(self, session_token):
        """
        Fetches and processes leaderboard data from the GameService.
        Returns a list of dictionaries containing rank, username, and points.
        """
        leaderboard = []
        try:
            if not session_token:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] [ERROR] Session token is null")
                return leaderboard

            # Fetch leaderboard entries from GameService
            entries = self.game_service.getLeaderboards(self.player.player_id, session_token)

            # Process entries
            for i, entry in enumerate(entries, 1):
                parts = entry.split(":")
                if len(parts) == 2:
                    username = parts[0]
                    try:
                        points = int(parts[1])
                    except ValueError:
                        with console_lock:
                            print(f"[CLIENT | {current_time()}] [ERROR] Failed to parse points for entry: {entry}")
                        continue
                    leaderboard.append({"rank": i, "username": username, "points": points})
                else:
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] [ERROR] Invalid leaderboard entry format: {entry}")

            # Display leaderboard table if not empty
            if leaderboard:
                self.print_leaderboard_table(leaderboard)
            else:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] [DEBUG] No valid leaderboard entries to display")

        except GameIDL.NotLoggedInException as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] [ERROR] NotLoggedInException while fetching leaderboard: {e}")
                print(f"[CLIENT | {current_time()}] [DEBUG] Player ID: {self.player.player_id if self.player else 'null'}, Session Token: {session_token}")
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] [ERROR] Unexpected error fetching leaderboard: {e}")

        with console_lock:
            print(f"[CLIENT | {current_time()}] [DEBUG] Returning {len(leaderboard)} leaderboard entries")
        return leaderboard

    def print_leaderboard_table(self, leaderboard):
        """
        Prints the leaderboard as a formatted table.
        """
        # Define column widths
        rank_width = 6
        username_width = 15
        points_width = 8

        # Print table header
        header = (
            f"[CLIENT | {current_time()}] [DEBUG] Leaderboard:\n"
            f"+-{'-' * rank_width}-+-{'-' * username_width}-+-{'-' * points_width}-+\n"
            f"| {'Rank':<{rank_width}} | {'Username':<{username_width}} | {'Points':<{points_width}} |\n"
            f"+-{'-' * rank_width}-+-{'-' * username_width}-+-{'-' * points_width}-+\n"
        )
        with console_lock:
            print(header, end='')

        # Print table rows
        for entry in leaderboard:
            with console_lock:
                print(
                    f"| {entry['rank']:<{rank_width}} | {entry['username']:<{username_width}} | {entry['points']:<{points_width}} |"
                )

        # Print table footer
        with console_lock:
            print(
                f"+-{'-' * rank_width}-+-{'-' * username_width}-+-{'-' * points_width}-+"
            )

    def get_current_user_info(self, session_token, leaderboard):
        """
        Retrieves and returns the current user's leaderboard information using the provided leaderboard data.
        Returns a dictionary with rank, username, and points, or None if not found.
        """
        try:
            username = self.player.username
            for entry in leaderboard:
                if entry["username"] == username:
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] [DEBUG] Updated current user info: {username}")
                    return {
                        "rank": entry["rank"],
                        "username": entry["username"],
                        "points": entry["points"]
                    }
            # Fallback if player not in leaderboard
            with console_lock:
                print(f"[CLIENT | {current_time()}] [DEBUG] User {username} not found in leaderboard")
            return {
                "rank": "N/A",
                "username": username,
                "points": 0
            }
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] [ERROR] Failed to update user info: {e}")
            return None