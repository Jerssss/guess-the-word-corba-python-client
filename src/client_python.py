import sys
import threading
import platform
import time
import re
import socket
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
import GameIDL
import PlayerCallBackIDL
import PlayerCallBackIDL__POA
from datetime import datetime
from about import About

# Lock for synchronizing console output
con_lock = threading.Lock()

# Flag to signal forced logout for menu refresh
forced_logout_flag = threading.Event()

# PlayerAccount class
class PlayerAccount:
    def __init__(self, player_id, username, password):
        self.player_id = player_id
        self.username = username
        self.password = password  # Store password for re-authentication
        self.game_wins = 0 

# SessionManager class
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

# Callback registration functions
def register_login_callback(poa, callback_servant):
    return poa.servant_to_reference(callback_servant)

def register_game_callback(poa, callback_servant):
    return poa.servant_to_reference(callback_servant)

def register_waiting_room_callback(poa, callback_servant):
    return poa.servant_to_reference(callback_servant)

# Login Callback Servant
class LoginCallbackServant(PlayerCallBackIDL__POA.LoginCallbackService):
    def notifyLoginSuccess(self, sessionToken, playerId):
        with con_lock:
            print(f"[Callback] Login successful for player {playerId} with token {sessionToken}")

    def notifyLoginFailure(self, reason):
        with con_lock:
            print(f"[Callback] Login failed: {reason}")

    def notifyForcedLogout(self, playerId, sessionToken):
        with con_lock:
            print(f"[Callback] Forced logout for player {playerId}, invalidating token: {sessionToken}")
            print("Another client may have logged in with the same credentials. Please ensure only one client is active.")
        SessionManager.set_session_token(None)  # Clear session token
        SessionManager.set_logged_in_player(None)  # Clear logged-in player
        forced_logout_flag.set()  # Signal to return to login
        time.sleep(2)  # Increased delay to stabilize server state

# Game Controller
class GameController:
    def __init__(self, game_service, player_id, session_token, game_token):
        self.game_service = game_service
        self.player_id = player_id
        self.session_token = session_token
        self.game_token = game_token
        self.total_rounds = self.get_setting("total_rounds")
        self.current_round = 0
        self.secret_word = ""
        self.revealed_word = []
        self.lives = 0
        self.round_time_limit = 0
        self.round_start_time = 0
        self.round_started = threading.Event()
        self.round_ended = threading.Event()
        self.game_ended = threading.Event()
        self.winner_name = ""
        self.champion = ""
        self.rounds_ended = set()  # Track ended rounds to prevent duplicates

    def get_setting(self, game_id):
        try:
            val = self.game_service.getSetting(game_id, self.session_token)
            if not val:
                with con_lock:
                    print(f"Warning: Setting {game_id} is empty, using default value.")
                return 60 if game_id == "round_time" else 0
            return int(val)
        except ValueError:
            with con_lock:
                print(f"Warning: Invalid {game_id} value, using default.")
            return 60 if game_id == "round_time" else 0
        except Exception as e:
            with con_lock:
                print(f"Warning: Error getting setting {game_id}: {e}, using default.")
            return 60 if game_id == "round_time" else 0

    def handle_round_start(self, round_no):
        if self.current_round == round_no:
            return  # Ignore duplicate round start callbacks
        self.current_round = round_no
        try:
            self.secret_word = self.game_service.getRandomWord(self.game_token, round_no, self.player_id, self.session_token)
            self.revealed_word = ['_'] * len(self.secret_word) # Set the no. of blanks
            self.lives = self.get_setting("number_of_lives")
            self.round_time_limit = self.get_setting("round_time")
            self.round_start_time = time.time()
            self.round_ended.clear()
            with con_lock:
                print(f"\nRound {round_no} started!")
                print(f"Word to guess: {' '.join(self.revealed_word)}")
                print(f"Lives: {self.lives}")
                print(f"Time limit: {self.round_time_limit} seconds")
            self.round_started.set()
        except Exception as e:
            with con_lock:
                print(f"Error starting round {round_no}: {e}")
            self.round_ended.set()

    def play_round(self, username):
        while not self.round_ended.is_set():
            if forced_logout_flag.is_set():
                with con_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            time_passed = time.time() - self.round_start_time
            rem_time = max(0, self.round_time_limit - time_passed)
            if rem_time <= 0:
                with con_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Time's up! Round over.")
                self.round_ended.set()
                break
            with con_lock:
                print(f"\n[CLIENT | {current_time()} | {username}] Word: {' '.join(self.revealed_word)}")
                print(f"[CLIENT | {current_time()} | {username}] Lives: {self.lives}")
                print(f"[CLIENT | {current_time()} | {username}] Time remaining: {int(rem_time)} seconds")
                print(f"[CLIENT | {current_time()} | {username}] Enter a letter (or 'quit' to leave): ", end='', flush=True)
            guess = input().strip().upper()
            if forced_logout_flag.is_set():
                with con_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            if guess == 'QUIT':
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Quitting the round...")
                self.round_ended.set()  # Signal round end on quit
                break
            if len(guess) != 1 or not guess.isalpha():
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid input. Please enter a single letter.")
                continue
            try:
                positions = self.game_service.guessLetter(self.game_token, self.player_id, self.session_token, guess)
                if positions:
                    # Validate positions to prevent index out of range
                    valid_positions = [pos for pos in positions if 0 <= pos < len(self.revealed_word)]
                    if len(valid_positions) < len(positions):
                        with con_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Error: Invalid positions {positions} for word length {len(self.revealed_word)}. Using valid positions {valid_positions}.")
                    for pos in valid_positions:
                        self.revealed_word[pos] = guess
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Correct! Word: {' '.join(self.revealed_word)}")
                        if '_' not in self.revealed_word:
                            print(f"[CLIENT | {current_time()} | {username}] You guessed the word!")
                            self.round_ended.set()
                            break
                else:
                    self.lives -= 1
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Incorrect. Lives left: {self.lives}")
                        if self.lives <= 0:
                            print(f"[CLIENT | {current_time()} | {username}] Out of lives!")
                            self.round_ended.set()
                            break
            except GameIDL.AlreadyGuessedLetterException:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Letter '{guess}' was already guessed. Try a different letter.")
                continue
            except GameIDL.MaxAttemptsReachedException:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Maximum attempts reached. Round over.")
                self.round_ended.set()
                break
            except Exception as e:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Error during guess: {e}")
                self.round_ended.set()  # Signal round end to avoid hang
                break

    def handle_round_end(self, winner_name, secret_word):
        if self.current_round in self.rounds_ended:
            return  # Ignore duplicate round end callbacks
        self.rounds_ended.add(self.current_round)
        self.winner_name = winner_name if winner_name else "Nobody"
        self.secret_word = secret_word
        self.round_ended.set()
        with con_lock:
            print(f"\nRound {self.current_round} ended. Winner: {self.winner_name}, Secret word: {secret_word}")
            if self.current_round < self.total_rounds:
                print("Waiting for the next round...")

    def handle_game_end(self, winner_name):
        self.champion = winner_name if winner_name else "Nobody"
        self.game_ended.set()
        with con_lock:
            print(f"\nGame ended. Overall winner: {self.champion}")

# Game Callback Servant
class GameCallbackServant(PlayerCallBackIDL__POA.GameCallBackService):
    def __init__(self, controller):
        self.controller = controller

    def notifyGameStart(self, gameToken, sessionToken):
        with con_lock:
            print(f"\n[Callback] Game started with token {gameToken}")

    def notifyRoundStart(self, gameToken, roundNumber, sessionToken):
        with con_lock:
            print(f"\n[Callback] Round {roundNumber} started")
        self.controller.handle_round_start(roundNumber)

    def notifyRoundEnd(self, gameToken, sessionToken, winnerName, secretWord):
        with con_lock:
            print(f"\n[Callback] Round ended. Winner: {winnerName}, Word: {secretWord}")
        self.controller.handle_round_end(winnerName, secretWord)

    def notifyGameEnd(self, gameToken, sessionToken, winnerName):
        with con_lock:
            print(f"\n[Callback] Game ended. Winner: {winnerName}")
        self.controller.handle_game_end(winnerName)

# Main client logic
def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def display_menu():
    with con_lock:
        print("\n=== Game Lobby ===")
        print("1. Start Game")
        print("2. View Leaderboard")
        print("3. About")
        print("4. Quit")
        print("(Type 'exit' to exit the client)")

def is_server_available(server_ip, port=1050, timeout=1):
    # Check if the server is reachable by attempting a TCP connection.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((server_ip, port))
        s.close()
        if result != 0:
            with con_lock:
                print(f"[CLIENT | {current_time()}] Server at {server_ip}:{port} is not reachable (error code: {result}).")
            return False
        return True
    except socket.error as e:
        with con_lock:
            print(f"[CLIENT | {current_time()}] Server at {server_ip}:{port} is not reachable: {e}")
        return False

def cleanup_orb():
    """Clean up the current ORB and ORB thread."""
    try:
        orb = SessionManager.get_orb()
        if orb:
            try:
                orb.shutdown(True)  # Wait for pending operations to complete
                time.sleep(1)  # Increased delay to ensure shutdown completes
                for _ in range(3):  # Retry destroy up to 3 times
                    try:
                        orb.destroy()
                        break
                    except Exception:
                        time.sleep(0.5)
            except Exception as e:
                with con_lock:
                    print(f"[CLIENT | {current_time()}] Warning: Error during ORB shutdown/destroy: {e}")
            SessionManager._orb = None
        orb_thread = SessionManager.get_orb_thread()
        if orb_thread and orb_thread.is_alive():
            orb_thread.join(timeout=10)  # Extended timeout for thread join
            if orb_thread.is_alive():
                with con_lock:
                    print(f"[CLIENT | {current_time()}] Warning: ORB thread did not terminate within 10 seconds.")
            SessionManager._orb_thread = None
        SessionManager._root_poa = None
        SessionManager.set_auth_service(None)
        SessionManager.set_game_service(None)
    except Exception as e:
        with con_lock:
            print(f"[CLIENT | {current_time()}] Error cleaning up ORB: {e}")

def initialize_orb(server_ip):
    """Initialize a new ORB with retries and return ORB, POA, and thread."""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            # Ensure any existing ORB is cleaned up
            cleanup_orb()
            
            # Initialize new ORB
            orb_args = sys.argv + ['-ORBInitRef', f'NameService=corbaloc::{server_ip}:1050/NameService']
            orb = CORBA.ORB_init(orb_args, CORBA.ORB_ID)
            
            # Initialize POA
            poa = orb.resolve_initial_references("RootPOA")
            if poa is None:
                raise Exception("RootPOA is None")
            poa._get_the_POAManager().activate()
            
            # Start ORB thread
            orb_thread = threading.Thread(target=orb.run)
            orb_thread.daemon = True
            orb_thread.start()
            
            # Verify ORB is running
            time.sleep(0.5)  # Brief delay to ensure thread starts
            if not orb_thread.is_alive():
                raise Exception("ORB thread failed to start")
            
            return orb, poa, orb_thread
        except Exception as e:
            with con_lock:
                print(f"[CLIENT | {current_time()}] ORB initialization attempt {attempt}/{max_retries} failed: {e}")
            cleanup_orb()
            if attempt < max_retries:
                time.sleep(1)
    with con_lock:
        print(f"[CLIENT | {current_time()}] Failed to initialize ORB after {max_retries} attempts.")
    return None, None, None

def reconnect_to_server(server_ip, username, password, current_token):
    """Attempt to reconnect to the server and verify with the existing session."""
    max_attempts = 5
    delay = 10  # Fixed 10-second delay
    for attempt in range(1, max_attempts + 1):
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Server connection lost. Attempting to reconnect (Attempt {attempt}/{max_attempts})...")

        # Check if forced logout occurred
        if forced_logout_flag.is_set():
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnection aborted due to forced logout.")
            return None

        # Check if server is reachable
        if not is_server_available(server_ip):
            if attempt < max_attempts:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Retrying in {delay} seconds...")
                time.sleep(delay)
            continue

        try:
            # Initialize new ORB
            orb, root_poa, orb_thread = initialize_orb(server_ip)
            if orb is None:
                raise Exception("Failed to initialize ORB")

            # Update SessionManager with new ORB
            SessionManager.init_orb(orb, root_poa, orb_thread)
            SessionManager.set_server_ip(server_ip)
            SessionManager.set_auth_service(None)
            SessionManager.set_game_service(None)

            # Resolve NameService and verify it's fully available
            obj = orb.resolve_initial_references("NameService")
            naming_context = obj._narrow(CosNaming.NamingContextExt)
            if naming_context is None:
                raise Exception("NamingContextExt narrowing returned None")

            # Verify NameService is responsive
            try:
                naming_context._non_existent()  # Check if NameService is alive
            except (CORBA.OBJECT_NOT_EXIST, CORBA.TRANSIENT):
                raise Exception("NameService is not fully available")

            # Resolve AuthenticationService
            auth_obj = naming_context.resolve_str("AuthenticationService")
            auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
            if auth_service is None:
                raise Exception("AuthenticationService narrowing returned None")

            # Resolve GameService
            game_obj = naming_context.resolve_str("GameService")
            game_service = game_obj._narrow(GameIDL.GameService)
            if game_service is None:
                raise Exception("GameService narrowing returned None")

            # Test existing session validity
            if current_token:
                session_token, player_id = current_token
                try:
                    game_service.getSetting("total_rounds", session_token)
                    # Update SessionManager
                    SessionManager.set_auth_service(auth_service)
                    SessionManager.set_game_service(game_service)
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Reconnected successfully with existing session.")
                    return current_token
                except Exception:
                    # Session invalid, proceed to re-authenticate
                    pass

            # Re-authenticate
            callback_servant = LoginCallbackServant()
            callback_ref = register_login_callback(root_poa, callback_servant)
            token = auth_service.login(username, password, callback_ref)
            player_id = token[1]
            session_token = token[0]
            player_account = PlayerAccount(player_id, username, password)
            SessionManager.set_session_token((session_token, player_id))
            SessionManager.set_logged_in_player(player_account)

            # Update SessionManager
            SessionManager.set_auth_service(auth_service)
            SessionManager.set_game_service(game_service)

            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnected and re-authenticated successfully. New token: {token}")
            return token

        except Exception as e:
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Reconnection attempt {attempt} failed: {e}")
            cleanup_orb()  # Ensure cleanup on failure
            if attempt < max_attempts:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Retrying in {delay} seconds...")
                time.sleep(delay)
            continue

    with con_lock:
        print(f"[CLIENT | {current_time()} | {username}] Failed to reconnect after {max_attempts} attempts. Returning to login.")
    SessionManager.set_session_token(None)
    SessionManager.set_logged_in_player(None)
    SessionManager.set_auth_service(None)
    SessionManager.set_game_service(None)
    cleanup_orb()  # Ensure ORB is cleaned up before returning
    return None

def reauthenticate(username, password, auth_service, poa):
    """Attempt to re-authenticate and return new token."""
    try:
        callback_servant = LoginCallbackServant()
        callback_ref = register_login_callback(poa, callback_servant)
        token = auth_service.login(username, password, callback_ref)
        player_id = token[1]
        session_token = token[0]
        player_account = PlayerAccount(player_id, username, password)
        SessionManager.set_session_token((session_token, player_id))
        SessionManager.set_logged_in_player(player_account)
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Re-authentication successful!")
            print(f"New token: {token}")
        return token
    except AuthenticationIDL.AlreadyLoggedInException:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Another client is already logged in. Please try again.")
        return None
    except AuthenticationIDL.AuthenticationException:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Re-authentication failed: Invalid credentials.")
        return None
    except Exception as e:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Re-authentication failed: {e}")
        return None

def check_server_connection(game_service, username, token):
    """Check if the server is responsive using a lightweight GameService call."""
    if not token:
        return False
    session_token, _ = token
    try:
        game_service.getSetting("total_rounds", session_token)
        return True
    except Exception as e:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Server connection check failed: {e}")
        return False

def start_game(game_service, username, token, auth_service):
    session_token, player_id = token
    with con_lock:
        print(f"[CLIENT | {current_time()} | {username}] Starting a new game...")
        print(f"[CLIENT | {current_time()} | {username}] Joining the waiting room...")

    try:
        if not SessionManager.get_session_token():
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Session token invalid. Please log in again.")
            return False

        time.sleep(0.5)  # Brief delay to avoid race conditions
        game_token = game_service.joinLobby(player_id, session_token)
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Joined waiting room: {game_token}")

        player_count = 0
        for remaining in range(10, -1, -1):
            try:
                player_count = game_service.getNumberOfPlayersJoined(player_id, session_token)
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
            except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Server disconnected during lobby: {e}")
                player = SessionManager.get_logged_in_player()
                if not player:
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] No player data available. Returning to login.")
                    return False
                new_token = reconnect_to_server(SessionManager.get_server_ip(), username, player.password, token)
                if not new_token:
                    return False
                token = new_token
                session_token, player_id = token
                game_service = SessionManager.get_game_service()
                auth_service = SessionManager.get_auth_service()
                # Rejoin lobby with new token
                game_token = game_service.joinLobby(player_id, session_token)
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Rejoined waiting room: {game_token}")
                player_count = game_service.getNumberOfPlayersJoined(player_id, session_token)
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
            time.sleep(1)
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Countdown finished. Current players: {player_count}")
            if player_count < 2:
                print(f"[CLIENT | {current_time()} | {username}] Not enough players joined within 10 seconds. Returning to home screen.")
                return True
            print(f"[CLIENT | {current_time()} | {username}] Enough players joined! Starting game...")

        controller = GameController(game_service, player_id, session_token, game_token)
        callback_servant = GameCallbackServant(controller)
        poa = SessionManager.get_poa()
        callback_ref = register_game_callback(poa, callback_servant)
        game_service.registerCallBack(player_id, game_token, session_token, callback_ref)

        game_service.startRound(game_token, 1, player_id, session_token)

        # Game loop adjusted to wait for game end
        while controller.current_round <= controller.total_rounds and not controller.game_ended.is_set() and not forced_logout_flag.is_set():
            if not controller.round_started.wait(timeout=30):
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to start. Exiting game.")
                break
            controller.round_started.clear()
            controller.play_round(username)
            if controller.current_round >= controller.total_rounds:
                break  # Exit loop if all rounds are complete
            if not controller.round_ended.wait(timeout=15):
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to end. Checking game status...")
                if controller.game_ended.is_set():
                    break
            controller.round_ended.clear()
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Round {controller.current_round} ended. Winner: {controller.winner_name}, Word: {controller.secret_word}")

        if not controller.game_ended.is_set() and not forced_logout_flag.is_set():
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Waiting for game to officially end...")
            if not controller.game_ended.wait(timeout=60):
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for game to end. Forcing exit.")
            else:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Game ended. Overall winner: {controller.champion}")
        else:
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] Game ended. Overall winner: {controller.champion}")

        return True

    except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Server disconnected during game: {e}")
        player = SessionManager.get_logged_in_player()
        if not player:
            with con_lock:
                print(f"[CLIENT | {current_time()} | {username}] No player data available. Returning to login.")
            return False
        new_token = reconnect_to_server(SessionManager.get_server_ip(), username, player.password, token)
        if not new_token:
            return False
        return start_game(SessionManager.get_game_service(), username, new_token, SessionManager.get_auth_service())

    except GameIDL.NotLoggedInException:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Session invalid (NotLoggedInException). Attempting to re-authenticate...")
        new_token = reauthenticate(username, SessionManager.get_logged_in_player().password, auth_service, SessionManager.get_poa())
        if new_token:
            return start_game(game_service, username, new_token, auth_service)
        return False
    except GameIDL.NotEnoughPlayersException:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Not enough players to start the game after waiting.")
        return True
    except Exception as e:
        with con_lock:
            print(f"[CLIENT | {current_time()} | {username}] Error during game: {e}")
        return True

def about():
    about_info = About()
    about_info.display()

def is_valid_ip_or_hostname(address):
    if not address:
        return True
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if re.match(ipv4_pattern, address):
        return True
    hostname_pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+$'
    if re.match(hostname_pattern, address) or address == "localhost":
        return True
    return False

def non_blocking_input(prompt):
    """Use blocking input with forced logout check to avoid hangs."""
    with con_lock:
        print(prompt, end='', flush=True)
    choice = input().strip()
    if forced_logout_flag.is_set():
        with con_lock:
            print(f"[CLIENT | {current_time()}] Forced logout detected. Checking session validity...")
        return None
    return choice

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
            print(f"[CLIENT | {current_time()}] Enter server IP address (or press Enter for default 'localhost'): ", end='')
            server_ip = input().strip() or "localhost"
            if not is_valid_ip_or_hostname(server_ip):
                with con_lock:
                    print(f"[CLIENT | {current_time()}] Invalid IP address or hostname: {server_ip}. Please enter a valid IPv4 address (e.g., 192.168.1.1) or hostname (e.g., localhost).")
                server_ip = None
                continue

        # Initialize ORB and services
        while not (orb and poa and orb_thread and auth_service and game_service):
            try:
                # Initialize ORB if not already initialized
                if not orb or not poa or not orb_thread:
                    orb, poa, orb_thread = initialize_orb(server_ip)
                    if orb is None:
                        with con_lock:
                            print(f"[CLIENT | {current_time()}] Failed to initialize ORB. Retrying in 2 seconds...")
                        time.sleep(2)
                        continue
                    SessionManager.init_orb(orb, poa, orb_thread)
                    SessionManager.set_server_ip(server_ip)
                    with con_lock:
                        print("Step 1: ORB initialized")

                # Resolve services if not already resolved
                if not auth_service or not game_service:
                    obj = orb.resolve_initial_references("NameService")
                    naming_context = obj._narrow(CosNaming.NamingContextExt)
                    if naming_context is None:
                        with con_lock:
                            print("FAILED: NamingContextExt narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    with con_lock:
                        print("Step 2: NameService resolved and narrowed")

                    auth_obj = naming_context.resolve_str("AuthenticationService")
                    auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
                    if auth_service is None:
                        with con_lock:
                            print("FAILED: AuthenticationService narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    SessionManager.set_auth_service(auth_service)
                    with con_lock:
                        print("Step 3: AuthenticationService resolved")

                    game_obj = naming_context.resolve_str("GameService")
                    game_service = game_obj._narrow(GameIDL.GameService)
                    if game_service is None:
                        with con_lock:
                            print("FAILED: GameService narrowing returned None")
                        cleanup_orb()
                        orb = None
                        poa = None
                        orb_thread = None
                        time.sleep(2)
                        continue
                    SessionManager.set_game_service(game_service)
                    with con_lock:
                        print("Step 4: GameService resolved")
                break  # Exit initialization loop if all components are set
            except (CORBA.TRANSIENT, CORBA.COMM_FAILURE, CORBA.OBJECT_NOT_EXIST) as e:
                with con_lock:
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
        while True:
            with con_lock:
                print("\n--- LOGIN ---")
                print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
            username = input().strip()
            if username.lower() == 'exit':
                with con_lock:
                    print("Exiting login client.")
                cleanup_orb()
                orb = None
                poa = None
                orb_thread = None
                auth_service = None
                game_service = None
                break

            with con_lock:
                print(f"[CLIENT | {current_time()}] Enter password: ", end='')
            password = input().strip()

            if not username or not password:
                with con_lock:
                    print(f"[CLIENT | {current_time()}] Username or password cannot be empty!")
                continue

            if forced_logout_flag.is_set():
                with con_lock:
                    print(f"[CLIENT | {current_time()}] Waiting due to recent forced logout. Please try again shortly.")
                forced_logout_flag.clear()
                time.sleep(2)
                continue

            try:
                # Validate ORB and POA
                if poa is None or orb is None or not orb_thread.is_alive():
                    with con_lock:
                        print(f"[CLIENT | {current_time()}] ORB or POA is invalid. Reinitializing ORB...")
                    cleanup_orb()
                    orb, poa, orb_thread = initialize_orb(server_ip)
                    if orb is None:
                        with con_lock:
                            print(f"[CLIENT | {current_time()}] Failed to reinitialize ORB. Retrying in 2 seconds...")
                        time.sleep(2)
                        break  # Break to reinitialize ORB and services
                    SessionManager.init_orb(orb, poa, orb_thread)
                    # Re-resolve services
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
                    with con_lock:
                        print(f"[CLIENT | {current_time()}] Reinitialized ORB and services successfully.")

                callback_servant = LoginCallbackServant()
                callback_ref = register_login_callback(poa, callback_servant)
                token = auth_service.login(username, password, callback_ref)
                player_id = token[1]
                session_token = token[0]
                player_account = PlayerAccount(player_id, username, password)
                SessionManager.set_session_token((session_token, player_id))
                SessionManager.set_logged_in_player(player_account)
                login_attempts = 0  # Reset attempts on success

                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Login successful!")
                    print(f"Token: {token}")
                    print("WARNING: Ensure only one client is running with these credentials to avoid forced logouts.")

                # Menu loop
                while True:
                    try:
                        # Check server connection before displaying menu
                        if not check_server_connection(game_service, username, token):
                            new_token = reconnect_to_server(SessionManager.get_server_ip(), username, password, token)
                            if not new_token:
                                break
                            token = new_token
                            auth_service = SessionManager.get_auth_service()
                            game_service = SessionManager.get_game_service()

                        display_menu()
                        choice = non_blocking_input(f"[CLIENT | {current_time()} | {username}] Select an option: ")
                        if choice is None:
                            # Check if session is still valid
                            if check_server_connection(game_service, username, token):
                                with con_lock:
                                    print(f"[CLIENT | {current_time()} | {username}] Session still valid. Continuing in lobby.")
                                continue
                            else:
                                with con_lock:
                                    print(f"[CLIENT | {current_time()} | {username}] Session invalid after forced logout. Attempting to reconnect...")
                                new_token = reconnect_to_server(SessionManager.get_server_ip(), username, password, token)
                                if not new_token:
                                    break
                                token = new_token
                                auth_service = SessionManager.get_auth_service()
                                game_service = SessionManager.get_game_service()
                                continue

                        if not choice:
                            continue
                        choice = choice.lower()
                        if choice == "1":
                            if not start_game(game_service, username, token, auth_service):
                                break
                        elif choice == "2":
                            with con_lock:
                                print("Leaderboard feature not implemented yet.")
                        elif choice == "3":
                            about()
                        elif choice == "4":
                            with con_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Logging Out...")
                            break
                        elif choice == "exit":
                            with con_lock:
                                print("Exiting login client.")
                            cleanup_orb()
                            orb = None
                            poa = None
                            orb_thread = None
                            auth_service = None
                            game_service = None
                            return
                        else:
                            with con_lock:
                                print(f"[CLIENT | {current_time()} | {username}] Invalid choice. Please enter 1, 2, 3, 4, or 'exit'.")
                    except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                        with con_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Server disconnected in menu: {e}")
                        new_token = reconnect_to_server(SessionManager.get_server_ip(), username, password, token)
                        if not new_token:
                            break
                        token = new_token
                        auth_service = SessionManager.get_auth_service()
                        game_service = SessionManager.get_game_service()

            except AuthenticationIDL.AlreadyLoggedInException:
                login_attempts += 1
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Already logged in. Another client may be active. Attempt {login_attempts}/{max_login_attempts}.")
                    print("Please ensure only one client is using these credentials.")
                if login_attempts >= max_login_attempts:
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Max login attempts reached. Please wait and try again.")
                    time.sleep(5)
                    login_attempts = 0
                else:
                    time.sleep(2)
                continue
            except AuthenticationIDL.AuthenticationException:
                with con_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid username or password.")
                login_attempts = 0
                continue
            except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                with con_lock:
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
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Login successful after reconnection!")
                        print(f"Token: {token}")
                        print("WARNING: Ensure only one client is running with these credentials to avoid forced logouts.")
                    # Continue to menu loop instead of breaking
                else:
                    with con_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Login failed: Unable to reconnect to server.")
                        print("Please try again or check server status.")
                    # Clear ORB and services to allow reinitialization
                    cleanup_orb()
                    orb = None
                    poa = None
                    orb_thread = None
                    auth_service = None
                    game_service = None
                    SessionManager.set_auth_service(None)
                    SessionManager.set_game_service(None)
                    time.sleep(2)
                    break  # Break to reinitialize ORB and services

if __name__ == "__main__":
    main()