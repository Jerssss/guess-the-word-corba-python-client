class GameService:
    def start_round(self, game_token, round_number, player_id, session_token):
        """Simulate starting a round"""
        print(f"Starting round {round_number} for player {player_id} with session token {session_token}")
        return round_number

    def guess_letter(self, game_token, player_id, session_token, letter):
        """Simulate a guess letter action"""
        print(f"Player {player_id} guessed letter: {letter}")
        return [1, 3]  # Simulated letter positions
