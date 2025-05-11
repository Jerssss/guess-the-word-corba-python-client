import time
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
import GameIDL
import PlayerCallBackIDL
import PlayerCallBackIDL__POA
from session import SessionManager
from player import PlayerAccount
from login import LoginManager
from game import GameManager
from connection import initialize_orb, reconnect_to_server, check_server_connection, cleanup_orb
from common import current_time, console_lock, forced_logout_flag
from utils import display_menu, is_valid_ip_or_hostname, non_blocking_input, about

def main():
    server_ip = None
    orb = None
    orb_thread = None
    poa = None
    auth_service = None
    game_service = None

    while True:
        # Prompt for server IP if not set
        if not server_ip:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Enter server IP address (or press Enter for default 'localhost'): ", end='')
            server_ip = input().strip() or "localhost"
            if not is_valid_ip_or_hostname(server_ip):
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Invalid IP address or hostname: {server_ip}. Please enter a valid IPv4 address (e.g., 192.168.1.1) or hostname (e.g., localhost).")
                server_ip = None
                continue

        # Initialize ORB and services
        while not (orb and poa and orb_thread and auth_service and game_service):
            try:
                if not orb or not poa or not orb_thread:
                    orb, poa, orb_thread = initialize_orb(server_ip)
                    if orb is None:
                        with console_lock:
                            print(f"[CLIENT | {current_time()}] Failed to initialize ORB. Retrying in 2 seconds...")
                        time.sleep(2)
                        continue
                    SessionManager.init_orb(orb, poa, orb_thread)
                    SessionManager.set_server_ip(server_ip)
                    with console_lock:
                        print("Step 1: ORB initialized")

                if not auth_service or not game_service:
                    obj = orb.resolve_initial_references("NameService")
                    naming_context = obj._narrow(CosNaming.NamingContextExt)
                    if naming_context is None:
                        with console_lock:
                            print("FAILED: NamingContextExt narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    with console_lock:
                        print("Step 2: NameService resolved and narrowed")

                    auth_obj = naming_context.resolve_str("AuthenticationService")
                    auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
                    if auth_service is None:
                        with console_lock:
                            print("FAILED: AuthenticationService narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    SessionManager.set_auth_service(auth_service)
                    with console_lock:
                        print("Step 3: AuthenticationService resolved")

                    game_obj = naming_context.resolve_str("GameService")
                    game_service = game_obj._narrow(GameIDL.GameService)
                    if game_service is None:
                        with console_lock:
                            print("FAILED: GameService narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    SessionManager.set_game_service(game_service)
                    with console_lock:
                        print("Step 4: GameService resolved")
                break
            except (CORBA.TRANSIENT, CORBA.COMM_FAILURE, CORBA.OBJECT_NOT_EXIST) as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Failed to connect to NameService at {server_ip}:1050: {e}")
                    print("Possible causes:")
                    print("- The server IP address or hostname is incorrect.")
                    print("- The server is not running or not listening on port 1050.")
                    print("- A network issue (e.g., firewall) is blocking the connection.")
                    print("Please verify the server is running and the IP/port are correct, then try again.")
                cleanup_orb()
                orb = None
                poa = None
                orb_thread = None
                auth_service = None
                game_service = None
                time.sleep(2)
                continue

        # Login loop
        login_attempts = 0
        max_login_attempts = 3
        login_manager = LoginManager(auth_service, poa)
        while True:
            # Check for forced logout before prompting for input
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Forced logout detected. Returning to login.")
                forced_logout_flag.clear()
                SessionManager.set_session_token(None)
                SessionManager.set_logged_in_player(None)
                continue  # Restart login loop without waiting for input

            with console_lock:
                print("\n--- LOGIN ---")
                print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
            username = input().strip()
            if username.lower() == 'exit':
                with console_lock:
                    print("Exiting login client.")
                cleanup_orb()
                return

            # Check again for forced logout before password prompt
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Forced logout detected. Returning to login.")
                forced_logout_flag.clear()
                SessionManager.set_session_token(None)
                SessionManager.set_logged_in_player(None)
                continue  # Restart login loop without waiting for input

            with console_lock:
                print(f"[CLIENT | {current_time()}] Enter password: ", end='')
            password = input().strip()

            if not username or not password:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Username or password cannot be empty!")
                continue

            try:
                if poa is None or orb is None or not orb_thread.is_alive():
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] ORB or POA is invalid. Reinitializing ORB...")
                    cleanup_orb()
                    orb, poa, orb_thread = initialize_orb(server_ip)
                    if orb is None:
                        with console_lock:
                            print(f"[CLIENT | {current_time()}] Failed to reinitialize ORB. Retrying in 2 seconds...")
                        time.sleep(2)
                        break
                    SessionManager.init_orb(orb, poa, orb_thread)
                    obj = orb.resolve_initial_references("NameService")
                    naming_context = obj._narrow(CosNaming.NamingContextExt)
                    if naming_context is None:
                        raise Exception("NamingContextExt narrowing returned None")
                    auth_obj = naming_context.resolve_str("AuthenticationService")
                    auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
                    if auth_service is None:
                        raise Exception("AuthenticationService narrowing returned None")
                    game_obj = naming_context.resolve_str("GameService")
                    game_service = game_obj._narrow(GameIDL.GameService)
                    if game_service is None:
                        raise Exception("GameService narrowing returned None")
                    SessionManager.set_auth_service(auth_service)
                    SessionManager.set_game_service(game_service)
                    login_manager = LoginManager(auth_service, poa)
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] Reinitialized ORB and services successfully.")

                token = login_manager.login(username, password)
                if not token:
                    login_attempts += 1
                    if login_attempts >= max_login_attempts:
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Max login attempts reached. Please wait and try again.")
                        time.sleep(5)
                        login_attempts = 0
                    continue
                login_attempts = 0

                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Login successful!")
                    print(f"Token: {token}")
                    print("WARNING: Ensure only one client is running with these credentials to avoid forced logouts.")

                # Menu loop
                game_manager = GameManager(game_service, auth_service, poa)
                while True:
                    try:
                        # Check for forced logout before any input or server check
                        if forced_logout_flag.is_set():
                            with console_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Forced logout detected. Returning to login.")
                            forced_logout_flag.clear()
                            SessionManager.set_session_token(None)
                            SessionManager.set_logged_in_player(None)
                            break

                        # Check server connection
                        if not check_server_connection(game_service, username, token):
                            new_token = reconnect_to_server(server_ip, username, password, token)
                            if not new_token:
                                with console_lock:
                                    print(f"[CLIENT | {current_time()} | {username}] Failed to reconnect. Returning to login.")
                                break
                            token = new_token
                            auth_service = SessionManager.get_auth_service()
                            game_service = SessionManager.get_game_service()
                            login_manager = LoginManager(auth_service, poa)
                            game_manager = GameManager(game_service, auth_service, poa)

                        # Display menu and get user choice
                        display_menu()
                        choice = non_blocking_input(f"[CLIENT | {current_time()} | {username}] Select an option: ")
                        if choice is None:
                            continue

                        if not choice:
                            continue
                        choice = choice.lower()
                        if choice == "1":
                            if not game_manager.start_game(username, token):
                                break
                        elif choice == "2":
                            with console_lock:
                                print("Leaderboard feature not implemented yet.")
                        elif choice == "3":
                            about()
                        elif choice == "4":
                            with console_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Logging Out...")
                            break
                        elif choice == "exit":
                            with console_lock:
                                print("Exiting login client.")
                            cleanup_orb()
                            return
                        else:
                            with console_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Invalid choice. Please enter 1, 2, 3, 4, or 'exit'.")
                    except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Server disconnected in menu: {e}")
                        new_token = reconnect_to_server(server_ip, username, password, token)
                        if not new_token:
                            with console_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Failed to reconnect. Returning to login.")
                            break
                        token = new_token
                        auth_service = SessionManager.get_auth_service()
                        game_service = SessionManager.get_game_service()
                        login_manager = LoginManager(auth_service, poa)
                        game_manager = GameManager(game_service, auth_service, poa)

            except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Server disconnected during login: {e}")
                new_token = reconnect_to_server(server_ip, username, password, None)
                if new_token:
                    SessionManager.set_session_token(new_token)
                    player_id = new_token[1]
                    player_account = PlayerAccount(player_id, username, password)
                    SessionManager.set_logged_in_player(player_account)
                    token = new_token
                    auth_service = SessionManager.get_auth_service()
                    game_service = SessionManager.get_game_service()
                    orb = SessionManager.get_orb()
                    poa = SessionManager.get_poa()
                    orb_thread = SessionManager.get_orb_thread()
                    login_manager = LoginManager(auth_service, poa)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Login successful after reconnection!")
                        print(f"Token: {token}")
                        print("WARNING: Ensure only one client is running with these credentials to avoid forced logouts.")
                else:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Login failed: Unable to reconnect to server.")
                        print("Please try again or check server status.")
                    cleanup_orb()
                    orb = None
                    poa = None
                    orb_thread = None
                    auth_service = None
                    game_service = None
                    SessionManager.set_auth_service(None)
                    SessionManager.set_game_service(None)
                    time.sleep(2)
                    break

if __name__ == "__main__":
    main()