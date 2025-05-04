# client/login_page_model.py

from Shared_Files import PlayerAccount, LoginResult

class LogInPageModel:
    def __init__(self, auth_service):
        self.auth_service = auth_service  # Use the passed auth_service

    def login(self, username, password, callback_stub):
        try:
            # Directly use auth_service for login (not calling PlayerClient_Python.get_authentication_service)
            session_token = self.auth_service.login(username, password, callback_stub)  # Call login method
            player_account = PlayerAccount(1, username, password, 100)  # Dummy player account
            return LoginResult(session_token, player_account)  # Return LoginResult object
        except Exception as ex:
            raise Exception(f"Login failed: {str(ex)}")
