import sys
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
import GameIDL
import PlayerCallBackIDL
from datetime import datetime
import time
from about import About

# SessionManager class integrated
class SessionManager:
    _session_token = None
    _game_token = None
    _logged_in_player = None
    _orb = None
    _root_poa = None
    _game_service = None
    _auth_service = None

    @staticmethod
    def init_orb(orb_ref, poa_ref):
        SessionManager._orb = orb_ref
        SessionManager._root_poa = poa_ref

    @staticmethod
    def get_orb():
        return SessionManager._orb

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

# Callback registration functions from PlayerClient_Model
def register_login_callback(poa, callback_servant):
    ref = poa.servant_to_reference(callback_servant)
    return PlayerCallBackIDL.LoginCallbackServiceHelper.narrow(ref)

def register_game_callback(poa, callback_servant):
    ref = poa.servant_to_reference(callback_servant)
    return PlayerCallBackIDL.GameCallBackServiceHelper.narrow(ref)

def register_waiting_room_callback(poa, callback_servant):
    ref = poa.servant_to_reference(callback_servant)
    return PlayerCallBackIDL.WaitingRoomGameCallbackServiceHelper.narrow(ref)

# Main client logic
def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def display_menu():
    print("\n=== Main Menu ===")
    print("1. Start Game")
    print("2. View Leaderboard")
    print("3. About")
    print("4. Quit")

def start_game(game_service, username, token):
    print(f"[CLIENT | {current_time()} | {username}] Starting a new game...")
    try:
        lobby_id = None
        print(f"[CLIENT | {current_time()} | {username}] Sending request to start game with token {token[1]} and lobby_id {lobby_id}")
        game_service.startGame(token[1], lobby_id)
        print(f"[CLIENT | {current_time()} | {username}] Game started successfully!")
        while True:
            try:
                player_count = game_service.getNumberOfPlayersJoined(lobby_id)
                print(f"[CLIENT | {current_time()} | {username}] Waiting for players... (Players: {player_count}/2)", end="\r")
                if player_count >= 2:
                    print(f"\n[CLIENT | {current_time()} | {username}] Minimum players reached. Starting countdown...")
                    for seconds in range(5, 0, -1):
                        print(f"[CLIENT | {current_time()} | {username}] Game starting in {seconds} seconds...", end="\r")
                        time.sleep(1)
                    print(f"[CLIENT | {current_time()} | {username}] Game starting now!")
                    break
            except GameIDL.NotEnoughPlayersException:
                print(f"[CLIENT | {current_time()} | {username}] Not enough players yet. Waiting...")
            time.sleep(1)
    except Exception as e:
        print(f"[CLIENT | {current_time()} | {username}] Error during game start: {e}")

def about():
    about_info = About()
    about_info.display()

def main():
    print(f"[CLIENT | {current_time()}] Enter server IP address (or press Enter for default 'localhost'): ", end='')
    server_ip = input().strip() or "localhost"

    # Initialize ORB
    orb_args = sys.argv + ['-ORBInitRef', f'NameService=corbaloc::{server_ip}:1050/NameService']
    orb = CORBA.ORB_init(orb_args, CORBA.ORB_ID)
    print("Step 1: ORB initialized")

    # Resolve RootPOA and activate POA Manager
    root_poa = orb.resolve_initial_references("RootPOA")
    root_poa._get_the_POAManager().activate()
    SessionManager.init_orb(orb, root_poa)

    # Resolve NameService
    obj = orb.resolve_initial_references("NameService")
    naming_context = obj._narrow(CosNaming.NamingContextExt)
    if naming_context is None:
        print("FAILED: NamingContextExt narrowing returned None")
        sys.exit(1)
    print("Step 2: NameService resolved and narrowed")

    # Resolve AuthenticationService
    auth_obj = naming_context.resolve_str("AuthenticationService")
    auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
    if auth_service is None:
        print("FAILED: AuthenticationService narrowing returned None")
        sys.exit(1)
    SessionManager.set_auth_service(auth_service)
    print("Step 3: AuthenticationService resolved")

    # Resolve GameService
    game_obj = naming_context.resolve_str("GameService")
    game_service = game_obj._narrow(GameIDL.GameService)
    if game_service is None:
        print("FAILED: GameService narrowing returned None")
        sys.exit(1)
    SessionManager.set_game_service(game_service)
    print("Step 4: GameService resolved")

    callback_ref = None  # Placeholder for callback implementation if needed

    while True:
        print("\n--- LOGIN ---")
        print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
        username = input().strip()
        if username.lower() == 'exit':
            print("Exiting login client.")
            break

        print(f"[CLIENT | {current_time()}] Enter password: ", end='')
        password = input().strip()

        try:
            token = auth_service.login(username, password, callback_ref)
            SessionManager.set_session_token(token)
            print(f"[CLIENT | {current_time()} | {username}] Login successful!")
            print(f"Token: {token}")

            while True:
                display_menu()
                choice = input(f"[CLIENT | {current_time()} | {username}] Select an option: ").strip()

                if choice == "1":
                    start_game(game_service, username, token)
                elif choice == "2":
                    print("Leaderboard feature not implemented yet.")
                elif choice == "3":
                    about()
                elif choice == "4":
                    print(f"[CLIENT | {current_time()} | {username}] Quitting...")
                    break
                else:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid choice. Please try again.")

        except AuthenticationIDL.AlreadyLoggedInException:
            print(f"[CLIENT | {current_time()} | {username}] Already logged in.")
        except AuthenticationIDL.AuthenticationException:
            print(f"[CLIENT | {current_time()}] Invalid username or password.")
        except Exception as e:
            print(f"[CLIENT | {current_time()}] Unexpected error: {e}")

    # Optional: Start ORB event loop if callbacks are implemented
    # orb.run()

if __name__ == "__main__":
    main()