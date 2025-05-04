class GameRoomController:
    def __init__(self, game_service, session_manager):
        self.game_service = game_service
        self.session_manager = session_manager

    def start_round(self, round_number):
        """Starts a round in the game room"""
        game_token = self.session_manager.get_game_token()
        player_id = self.session_manager.get_logged_in_player().get_player_id()
        session_token = self.session_manager.get_session_token()
        
        print(f"Starting round {round_number} for player {player_id}")
        return self.game_service.start_round(game_token, round_number, player_id, session_token)

    def guess_letter(self, letter):
        """Handles guessing a letter in the game"""
        game_token = self.session_manager.get_game_token()
        player_id = self.session_manager.get_logged_in_player().get_player_id()
        session_token = self.session_manager.get_session_token()
        
        print(f"Player {player_id} is guessing the letter: {letter}")
        return self.game_service.guess_letter(game_token, player_id, session_token, letter)

    def get_round_winner(self):
        """Gets the winner of the current round"""
        game_token = self.session_manager.get_game_token()
        player_id = self.session_manager.get_logged_in_player().get_player_id()
        session_token = self.session_manager.get_session_token()
        
        winner = self.game_service.get_round_winner(game_token, player_id, session_token)
        print(f"The winner of the round is: {winner}")
        return winner
