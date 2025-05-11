import sys
import threading
import socket
import time
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
import GameIDL
from common import current_time, console_lock, forced_logout_flag
from session import SessionManager
from login import LoginManager

def is_server_available(server_ip, port=1050, timeout=1):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((server_ip, port))
        s.close()
        if result != 0:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Server at {server_ip}:{port} is not reachable (error code: {result}).")
            return False
        return True
    except socket.error as e:
        with console_lock:
            print(f"[CLIENT | {current_time()}] Server at {server_ip}:{port} is not reachable: {e}")
        return False

def cleanup_orb():
    try:
        orb = SessionManager.get_orb()
        if orb:
            try:
                orb.shutdown(True)
                time.sleep(1)
                for _ in range(3):
                    try:
                        orb.destroy()
                        break
                    except Exception:
                        time.sleep(0.5)
            except Exception as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Warning: Error during ORB shutdown/destroy: {e}")
            SessionManager._orb = None
        orb_thread = SessionManager.get_orb_thread()
        if orb_thread and orb_thread.is_alive():
            orb_thread.join(timeout=10)
            if orb_thread.is_alive():
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Warning: ORB thread did not terminate within 10 seconds.")
            SessionManager._orb_thread = None
        SessionManager._root_poa = None
        SessionManager.set_auth_service(None)
        SessionManager.set_game_service(None)
    except Exception as e:
        with console_lock:
            print(f"[CLIENT | {current_time()}] Error cleaning up ORB: {e}")

def initialize_orb(server_ip):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            cleanup_orb()
            orb_args = sys.argv + ['-ORBInitRef', f'NameService=corbaloc::{server_ip}:1050/NameService']
            orb = CORBA.ORB_init(orb_args, CORBA.ORB_ID)
            poa = orb.resolve_initial_references("RootPOA")
            if poa is None:
                raise Exception("RootPOA is None")
            poa._get_the_POAManager().activate()
            orb_thread = threading.Thread(target=orb.run)
            orb_thread.daemon = True
            orb_thread.start()
            time.sleep(0.5)
            if not orb_thread.is_alive():
                raise Exception("ORB thread failed to start")
            return orb, poa, orb_thread
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] ORB initialization attempt {attempt}/{max_retries} failed: {e}")
            cleanup_orb()
            if attempt < max_retries:
                time.sleep(1)
    with console_lock:
        print(f"[CLIENT | {current_time()}] Failed to initialize ORB after {max_retries} attempts.")
    return None, None, None

def reconnect_to_server(server_ip, username, password, current_token):
    max_attempts = 5
    delay = 10
    for attempt in range(1, max_attempts + 1):
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Server connection lost. Attempting to reconnect (Attempt {attempt}/{max_attempts})...")

        if forced_logout_flag.is_set():
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnection aborted due to forced logout.")
            return None

        if not is_server_available(server_ip):
            if attempt < max_attempts:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Retrying in {delay} seconds...")
                time.sleep(delay)
            continue

        try:
            orb, root_poa, orb_thread = initialize_orb(server_ip)
            if orb is None:
                raise Exception("Failed to initialize ORB")

            SessionManager.init_orb(orb, root_poa, orb_thread)
            SessionManager.set_server_ip(server_ip)
            SessionManager.set_auth_service(None)
            SessionManager.set_game_service(None)

            obj = orb.resolve_initial_references("NameService")
            naming_context = obj._narrow(CosNaming.NamingContextExt)
            if naming_context is None:
                raise Exception("NamingContextExt narrowing returned None")

            try:
                naming_context._non_existent()
            except (CORBA.OBJECT_NOT_EXIST, CORBA.TRANSIENT):
                raise Exception("NameService is not fully available")

            auth_obj = naming_context.resolve_str("AuthenticationService")
            auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
            if auth_service is None:
                raise Exception("AuthenticationService narrowing returned None")

            game_obj = naming_context.resolve_str("GameService")
            game_service = game_obj._narrow(GameIDL.GameService)
            if game_service is None:
                raise Exception("GameService narrowing returned None")

            if current_token:
                session_token, player_id = current_token
                try:
                    game_service.getSetting("total_rounds", session_token)
                    SessionManager.set_auth_service(auth_service)
                    SessionManager.set_game_service(game_service)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Reconnected successfully with existing session.")
                    return current_token
                except Exception:
                    pass

            login_manager = LoginManager(auth_service, root_poa)
            token = login_manager.login(username, password)
            if not token:
                raise Exception("Re-authentication failed")

            SessionManager.set_auth_service(auth_service)
            SessionManager.set_game_service(game_service)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnected and re-authenticated successfully. New token: {token}")
            return token

        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnection attempt {attempt} failed: {e}")
            cleanup_orb()
            if attempt < max_attempts:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Retrying in {delay} seconds...")
                time.sleep(delay)
            continue

    with console_lock:
        print(f"[CLIENT | {current_time()} | {username}] Failed to reconnect after {max_attempts} attempts. Returning to login.")
    SessionManager.set_session_token(None)
    SessionManager.set_logged_in_player(None)
    SessionManager.set_auth_service(None)
    SessionManager.set_game_service(None)
    cleanup_orb()
    return None

def check_server_connection(game_service, username, token):
    if not token:
        return False
    session_token, _ = token
    try:
        game_service.getSetting("total_rounds", session_token)
        return True
    except Exception as e:
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Server connection check failed: {e}")
        return False