class GameLobbyController:
    def __init__(self, game_service):
        self.game_service = game_service

    def join_lobby(self, player_account, game_token):
        """Handles a player joining the lobby"""
        print(f"{player_account.get_display_name()} is joining the lobby with game token: {game_token}")

    def update_lobby(self):
        """Updates the lobby (e.g., display players, games, etc.)"""
        print("Updating the game lobby...")
        
    def start_game(self, game_token, player_id):
        """Starts a game from the lobby"""
        print(f"Starting game with token {game_token} for player {player_id}")
        return self.game_service.start_round(game_token, 1, player_id, "mock_session_token")
