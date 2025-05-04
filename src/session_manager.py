class SessionManager:
    game_token = None
    session_token = None
    logged_in_player = None

    @staticmethod
    def init_services(game_service, auth_service):
        SessionManager.game_service = game_service
        SessionManager.auth_service = auth_service

    @staticmethod
    def set_session_token(token):
        SessionManager.session_token = token

    @staticmethod
    def get_session_token():
        return SessionManager.session_token

    @staticmethod
    def set_game_token(token):
        SessionManager.game_token = token

    @staticmethod
    def get_game_token():
        return SessionManager.game_token

    @staticmethod
    def set_logged_in_player(player_account):
        SessionManager.logged_in_player = player_account

    @staticmethod
    def get_logged_in_player():
        return SessionManager.logged_in_player
