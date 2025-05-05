# client/login_callback_service.py

class LoginCallBackServiceImpl:
    def notify_forced_logout(self, player_id, session_token):
        print(f"[DEBUG][LoginCallBackService] notifyForcedLogout() called for player {player_id}, sessionToken={session_token}")
        
        # Instead of showing an alert, we'll print a message to the console
        print("[INFO] You have been logged out because you signed in elsewhere.")
        print(f"Player ID: {player_id}, Session Token: {session_token}")
        
        # Simulate navigation by printing the next step in the console
        print("[INFO] Logging out and redirecting to login...")
