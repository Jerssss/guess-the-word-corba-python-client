from login_callback_service import LoginCallBackServiceImpl
from session_manager import SessionManager
from Idls import AuthenticationIDL  # Importing the required CORBA helpers

class LogInController:
    def __init__(self, model, client):
        self.model = model
        self.client = client  # Assuming client is passed as a parameter and it manages CORBA connections

    def on_continue(self):
        # Collect user input via the console
        user = input("Enter username: ")
        password = input("Enter password: ")

        if not user or not password:
            print("Username/password cannot be empty!")
            return

        try:
            # Register callback servant for forced logout handling
            callback_service_impl = LoginCallBackServiceImpl()
            
            # Use your Client_Python instance to get the callback object reference
            callback_obj_ref = self.client.register_login_callback(callback_service_impl)
            
            # Assuming `AuthenticationIDL.LoginCallbackServiceHelper.narrow()` is available
            # and `self.client.register_login_callback()` gives you the callback reference.
            callback_stub = AuthenticationIDL.LoginCallbackServiceHelper.narrow(callback_obj_ref)

            # Invoke model to perform login with the callback stub
            result = self.model.login(user, password, callback_stub)

            # Store session token and logged-in player
            SessionManager.set_session_token(result.session_token)
            SessionManager.set_logged_in_player(result.account)

            # Output login success and session token
            print("Login successful!")
            print(f"Session Token: {result.session_token}")

            # Here, instead of navigating in a UI, we print a success message
            print("Redirecting to the game lobby...")

        except Exception as ex:
            print(f"Login failed: {str(ex)}")
