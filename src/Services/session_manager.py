# File: Services/session_manager.py

class SessionManager:
    _orb = None
    _poa = None
    _session_token = None
    _game_token = None
    _logged_in_player = None
    _game_service = None
    _auth_service = None

    @classmethod
    def init_orb(cls, orb_ref, poa_ref):
        cls._orb = orb_ref
        cls._poa = poa_ref

    @classmethod
    def get_orb(cls):
        return cls._orb

    @classmethod
    def get_poa(cls):
        return cls._poa

    @classmethod
    def set_session_token(cls, token):
        cls._session_token = token

    @classmethod
    def get_session_token(cls):
        return cls._session_token

    @classmethod
    def set_game_token(cls, token):
        cls._game_token = token

    @classmethod
    def get_game_token(cls):
        return cls._game_token

    @classmethod
    def set_logged_in_player(cls, player_account):
        cls._logged_in_player = player_account

    @classmethod
    def get_logged_in_player(cls):
        return cls._logged_in_player

    @classmethod
    def set_game_service(cls, service):
        cls._game_service = service

    @classmethod
    def get_game_service(cls):
        return cls._game_service

    @classmethod
    def set_auth_service(cls, service):
        cls._auth_service = service

    @classmethod
    def get_auth_service(cls):
        return cls._auth_service