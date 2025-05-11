import threading
import time
from omniORB import CORBA
import AuthenticationIDL
import PlayerCallBackIDL__POA
from common import current_time, console_lock, forced_logout_flag
from player import PlayerAccount
from session import SessionManager

class LoginCallbackServant(PlayerCallBackIDL__POA.LoginCallbackService):
    def notifyLoginSuccess(self, sessionToken, playerId):
        with console_lock:
            print(f"[Callback] Login successful for player {playerId} with token {sessionToken}")

    def notifyLoginFailure(self, reason):
        with console_lock:
            print(f"[Callback] Login failed: {reason}")

    def notifyForcedLogout(self, playerId, sessionToken):
        with console_lock:
            print(f"[Callback] Forced logout for player {playerId}, invalidating token: {sessionToken}")
            print("Another client may have logged in with the same credentials. Please ensure only one client is active.")
        SessionManager.set_session_token(None)
        SessionManager.set_logged_in_player(None)
        forced_logout_flag.set()

class LoginManager:
    def __init__(self, auth_service, poa):
        self.auth_service = auth_service
        self.poa = poa

    def register_login_callback(self, callback_servant):
        return self.poa.servant_to_reference(callback_servant)

    def login(self, username, password):
        try:
            callback_servant = LoginCallbackServant()
            callback_ref = self.register_login_callback(callback_servant)
            token = self.auth_service.login(username, password, callback_ref)
            player_id = token[1]
            session_token = token[0]
            player_account = PlayerAccount(player_id, username, password)
            SessionManager.set_session_token((session_token, player_id))
            SessionManager.set_logged_in_player(player_account)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Login successful!")
                print(f"Token: {token}")
            return token
        except AuthenticationIDL.AlreadyLoggedInException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Already logged in. Another client may be active.")
            return None
        except AuthenticationIDL.AuthenticationException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Invalid username or password.")
            return None
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Login failed: {e}")
            return None

    def reauthenticate(self, username, password):
        try:
            callback_servant = LoginCallbackServant()
            callback_ref = self.register_login_callback(callback_servant)
            token = self.auth_service.login(username, password, callback_ref)
            player_id = token[1]
            session_token = token[0]
            player_account = PlayerAccount(player_id, username, password)
            SessionManager.set_session_token((session_token, player_id))
            SessionManager.set_logged_in_player(player_account)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Re-authentication successful!")
                print(f"Token: {token}")
            return token
        except AuthenticationIDL.AlreadyLoggedInException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Another client is already logged in. Please try again.")
            return None
        except AuthenticationIDL.AuthenticationException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Re-authentication failed: Invalid credentials.")
            return None
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Re-authentication failed: {e}")
            return None