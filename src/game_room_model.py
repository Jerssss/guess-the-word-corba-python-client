class GameRoomModel:
    def __init__(self, game_service):
        self.game_service = game_service

    def register_callback(self, callback):
        """Registers a callback for the game"""
        print(f"Registering callback for player {callback.get_player_id()}")

    def start_round(self, game_token, round_number, player_id, session_token):
        """Starts a round in the game"""
        return self.game_service.start_round(game_token, round_number, player_id, session_token)

    def get_round_duration(self, session_token):
        """Gets the duration of the round"""
        return 60  # Simulating a fixed round duration

    def get_random_word(self, game_token, round_number, player_id, session_token):
        """Gets a random word for the round"""
        return "Python"

    def get_total_rounds(self, session_token):
        """Gets the total number of rounds"""
        return 10

    def guess_letter(self, game_token, player_id, session_token, letter):
        """Handles the letter guessing"""
        return [1, 3]  # Simulating letter positions

    def get_number_of_lives(self, session_token):
        """Gets the number of lives left"""
        return 3

    def get_round_winner(self, game_token, player_id, session_token):
        """Gets the winner of the round"""
        return "Player 1"

    def get_player_display_name(self, player_id, session_token):
        """Gets the display name of a player"""
        return f"Player {player_id}"

    def get_next_round_delay(self, session_token):
        """Gets the delay before the next round"""
        return 5  # Simulating a 5 second delay
