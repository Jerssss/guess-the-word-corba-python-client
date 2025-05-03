class PlayerAccount:
    """
    Represents a player account with credentials and stats.
    """

    def __init__(self, player_id, username, password, game_wins):
        """
        Constructor: sets the player ID and credentials.
        
        :param player_id: unique ID assigned by server
        :param username: login name
        :param password: login password
        :param game_wins: initial number of wins
        """
        self._player_id = player_id
        self._username = username
        self._password = password
        self._game_wins = game_wins

    @property
    def player_id(self):
        return self._player_id

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def game_wins(self):
        return self._game_wins

    @game_wins.setter
    def game_wins(self, value):
        self._game_wins = value