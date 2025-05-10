class PlayerAccount:
    def __init__(self, player_id, username, password):
        self.player_id = player_id
        self.username = username
        self.password = password
        self.game_wins = 0