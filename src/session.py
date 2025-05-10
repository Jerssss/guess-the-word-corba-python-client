import threading

class SessionManager:
    _session_token = None
    _game_token = None
    _logged_in_player = None
    _orb = None
    _orb_thread = None
    _root_poa = None
    _game_service = None
    _auth_service = None
    _server_ip = None

    @staticmethod
    def init_orb(orb_ref, poa_ref, orb_thread_ref):
        SessionManager._orb = orb_ref
        SessionManager._root_poa = poa_ref
        SessionManager._orb_thread = orb_thread_ref

    @staticmethod
    def get_orb():
        return SessionManager._orb

    @staticmethod
    def get_orb_thread():
        return SessionManager._orb_thread

    @staticmethod
    def get_poa():
        return SessionManager._root_poa

    @staticmethod
    def set_session_token(token):
        SessionManager._session_token = token

    @staticmethod
    def get_session_token():
        return SessionManager._session_token

    @staticmethod
    def set_game_token(token):
        SessionManager._game_token = token

    @staticmethod
    def get_game_token():
        return SessionManager._game_token

    @staticmethod
    def set_logged_in_player(player_account):
        SessionManager._logged_in_player = player_account

    @staticmethod
    def get_logged_in_player():
        return SessionManager._logged_in_player

    @staticmethod
    def set_game_service(game_service):
        SessionManager._game_service = game_service

    @staticmethod
    def get_game_service():
        return SessionManager._game_service

    @staticmethod
    def set_auth_service(auth_service):
        SessionManager._auth_service = auth_service

    @staticmethod
    def get_auth_service():
        return SessionManager._auth_service

    @staticmethod
    def set_server_ip(server_ip):
        SessionManager._server_ip = server_ip

    @staticmethod
    def get_server_ip():
        return SessionManager._server_ip