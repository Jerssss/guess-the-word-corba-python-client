import sys
import threading
import platform
import time
import re
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
import GameIDL
import PlayerCallBackIDL
import PlayerCallBackIDL__POA
from datetime import datetime
from about import About

# Lock for synchronizing console output
console_lock = threading.Lock()

# Flag to signal forced logout for menu refresh
forced_logout_flag = threading.Event()

# PlayerAccount class to mimic Java's Shared_Files.PlayerAccount
class PlayerAccount:
    def __init__(self, player_id, username):
        self.player_id = player_id
        self.username = username
        self.password = ""  # Placeholder, not stored
        self.game_wins = 0  # Matches Java's gameWins

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
        with console_lock:
            print(f"[Callback] Login successful for player {playerId} with token {sessionToken}")

    def notifyLoginFailure(self, reason):
        with console_lock:
            print(f"[Callback] Login failed: {reason}")

    def notifyForcedLogout(self, playerId, sessionToken):
        with console_lock:
            print(f"[Callback] Forced logout for player {playerId}, invalidating token: {sessionToken}")
            print("Another client may have logged in with the same credentials. Please ensure only one client is active.")
        SessionManager.set_session_token(None)  # Clear session token
        SessionManager.set_logged_in_player(None)  # Clear logged-in player
        forced_logout_flag.set()  # Signal to return to login
        time.sleep(2)  # Increased delay to stabilize server state

# Game Controller to manage game state and logic
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

    def get_setting(self, key):
        try:
            value = self.game_service.getSetting(key, self.session_token)
            if not value:
                with console_lock:
                    print(f"Warning: Setting {key} is empty, using default value.")
                return 60 if key == "round_time" else 0
            return int(value)
        except ValueError:
            with console_lock:
                print(f"Warning: Invalid {key} value, using default.")
            return 60 if key == "round_time" else 0
        except Exception as e:
            with console_lock:
                print(f"Warning: Error getting setting {key}: {e}, using default.")
            return 60 if key == "round_time" else 0

    def handle_round_start(self, round_number):
        if self.current_round == round_number:
            return  # Ignore duplicate round start callbacks
        self.current_round = round_number
        try:
            self.secret_word = self.game_service.getRandomWord(self.game_token, round_number, self.player_id, self.session_token)
            self.revealed_word = ['_'] * len(self.secret_word)
            self.lives = self.get_setting("number_of_lives")
            self.round_time_limit = self.get_setting("round_time")
            self.round_start_time = time.time()
            self.round_ended.clear()
            with console_lock:
                print(f"\nRound {round_number} started!")
                print(f"Word to guess: {' '.join(self.revealed_word)}")
                print(f"Lives: {self.lives}")
                print(f"Time limit: {self.round_time_limit} seconds")
            self.round_started.set()
        except Exception as e:
            with console_lock:
                print(f"Error starting round {round_number}: {e}")
            self.round_ended.set()

    def play_round(self, username):
        while not self.round_ended.is_set():
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            elapsed_time = time.time() - self.round_start_time
            remaining_time = max(0, self.round_time_limit - elapsed_time)
            if remaining_time <= 0:
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Time's up! Round over.")
                self.round_ended.set()
                break
            with console_lock:
                print(f"\n[CLIENT | {current_time()} | {username}] Word: {' '.join(self.revealed_word)}")
                print(f"[CLIENT | {current_time()} | {username}] Lives: {self.lives}")
                print(f"[CLIENT | {current_time()} | {username}] Time remaining: {int(remaining_time)} seconds")
                print(f"[CLIENT | {current_time()} | {username}] Enter a letter (or 'quit' to leave): ", end='', flush=True)
            guess = input().strip().upper()
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            if guess == 'QUIT':
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Quitting the round...")
                self.round_ended.set()  # Signal round end on quit
                break
            if len(guess) != 1 or not guess.isalpha():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid input. Please enter a single letter.")
                continue
            try:
                positions = self.game_service.guessLetter(self.game_token, self.player_id, self.session_token, guess)
                if positions:
                    # Validate positions to prevent index out of range
                    valid_positions = [pos for pos in positions if 0 <= pos < len(self.revealed_word)]
                    if len(valid_positions) < len(positions):
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Error: Invalid positions {positions} for word length {len(self.revealed_word)}. Using valid positions {valid_positions}.")
                    for pos in valid_positions:
                        self.revealed_word[pos] = guess
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Correct! Word: {' '.join(self.revealed_word)}")
                        if '_' not in self.revealed_word:
                            print(f"[CLIENT | {current_time()} | {username}] You guessed the word!")
                            self.round_ended.set()
                            break
                else:
                    self.lives -= 1
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Incorrect. Lives left: {self.lives}")
                        if self.lives <= 0:
                            print(f"[CLIENT | {current_time()} | {username}] Out of lives!")
                            self.round_ended.set()
                            break
            except GameIDL.AlreadyGuessedLetterException:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Letter '{guess}' was already guessed. Try a different letter.")
                continue
            except GameIDL.MaxAttemptsReachedException:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Maximum attempts reached. Round over.")
                self.round_ended.set()
                break
            except Exception as e:
                with console_lock:
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
        with console_lock:
            print(f"\nRound {self.current_round} ended. Winner: {self.winner_name}, Secret word: {secret_word}")
            if self.current_round < self.total_rounds:
                print("Waiting for the next round...")

    def handle_game_end(self, winner_name):
        self.champion = winner_name if winner_name else "Nobody"
        self.game_ended.set()
        with console_lock:
            print(f"\nGame ended. Overall winner: {self.champion}")

# Game Callback Servant
class GameCallbackServant(PlayerCallBackIDL__POA.GameCallBackService):
    def __init__(self, controller):
        self.controller = controller

    def notifyGameStart(self, gameToken, sessionToken):
        with console_lock:
            print(f"\n[Callback] Game started with token {gameToken}")

    def notifyRoundStart(self, gameToken, roundNumber, sessionToken):
        with console_lock:
            print(f"\n[Callback] Round {roundNumber} started")
        self.controller.handle_round_start(roundNumber)

    def notifyRoundEnd(self, gameToken, sessionToken, winnerName, secretWord):
        with console_lock:
            print(f"\n[Callback] Round ended. Winner: {winnerName}, Word: {secretWord}")
        self.controller.handle_round_end(winnerName, secretWord)

    def notifyGameEnd(self, gameToken, sessionToken, winnerName):
        with console_lock:
            print(f"\n[Callback] Game ended. Winner: {winnerName}")
        self.controller.handle_game_end(winnerName)

# Main client logic
def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def display_menu():
    with console_lock:
        print("\n=== Game Lobby ===")
        print("1. Start Game")
        print("2. View Leaderboard")
        print("3. About")
        print("4. Quit")
        print("(Type 'exit' to exit the client)")

def reauthenticate(username, password, auth_service, poa):
    """Attempt to re-authenticate and return new token."""
    try:
        callback_servant = LoginCallbackServant()
        callback_ref = register_login_callback(poa, callback_servant)
        token = auth_service.login(username, password, callback_ref)
        player_id = token[1]
        session_token = token[0]
        player_account = PlayerAccount(player_id, username)
        SessionManager.set_session_token((session_token, player_id))
        SessionManager.set_logged_in_player(player_account)
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Re-authentication successful!")
            print(f"New token: {token}")
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

def start_game(game_service, username, token, auth_service):
    session_token, player_id = token
    with console_lock:
        print(f"[CLIENT | {current_time()} | {username}] Starting a new game...")
        print(f"[CLIENT | {current_time()} | {username}] Joining the waiting room...")

    try:
        if not SessionManager.get_session_token():
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Session token invalid. Please log in again.")
            return False

        time.sleep(0.5)  # Brief delay to avoid race conditions
        game_token = game_service.joinLobby(player_id, session_token)
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Joined waiting room: {game_token}")

        player_count = 0
        for remaining in range(10, -1, -1):
            player_count = game_service.getNumberOfPlayersJoined(player_id, session_token)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
            time.sleep(1)
        with console_lock:
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

        # Game loop adjusted to exit after last round
        while controller.current_round <= controller.total_rounds and not controller.game_ended.is_set() and not forced_logout_flag.is_set():
            if not controller.round_started.wait(timeout=30):
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to start. Exiting game.")
                break
            controller.round_started.clear()
            controller.play_round(username)
            if controller.current_round >= controller.total_rounds:
                break  # Exit loop if all rounds are complete
            if not controller.round_ended.wait(timeout=10):  # Reduced timeout to 10 seconds
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to end. Exiting game.")
                break
            controller.round_ended.clear()
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Round {controller.current_round} ended. Winner: {controller.winner_name}, Word: {controller.secret_word}")

        if not controller.game_ended.is_set() and not forced_logout_flag.is_set() and not controller.game_ended.wait(timeout=10):  # Reduced timeout
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for game to end. Exiting.")
        else:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Game ended. Overall winner: {controller.champion}")

        return True

    except GameIDL.NotLoggedInException:
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Session invalid (NotLoggedInException). Attempting to re-authenticate...")
        new_token = reauthenticate(username, "1", auth_service, SessionManager.get_poa())
        if new_token:
            return start_game(game_service, username, new_token, auth_service)
        return False
    except GameIDL.NotEnoughPlayersException:
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Not enough players to start the game after waiting.")
        return True
    except Exception as e:
        with console_lock:
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
    with console_lock:
        print(prompt, end='', flush=True)
    choice = input().strip()
    if forced_logout_flag.is_set():
        forced_logout_flag.clear()
        return None
    return choice

def main():
    while True:
        print(f"[CLIENT | {current_time()}] Enter server IP address (or press Enter for default 'localhost'): ", end='')
        server_ip = input().strip() or "localhost"
        if not is_valid_ip_or_hostname(server_ip):
            with console_lock:
                print(f"[CLIENT | {current_time()}] Invalid IP address or hostname: {server_ip}. Please enter a valid IPv4 address (e.g., 192.168.1.1) or hostname (e.g., localhost).")
            continue

        try:
            orb_args = sys.argv + ['-ORBInitRef', f'NameService=corbaloc::{server_ip}:1050/NameService']
            orb = CORBA.ORB_init(orb_args, CORBA.ORB_ID)
            with console_lock:
                print("Step 1: ORB initialized")

            root_poa = orb.resolve_initial_references("RootPOA")
            root_poa._get_the_POAManager().activate()
            SessionManager.init_orb(orb, root_poa)

            orb_thread = threading.Thread(target=orb.run)
            orb_thread.daemon = True
            orb_thread.start()

            obj = orb.resolve_initial_references("NameService")
            naming_context = obj._narrow(CosNaming.NamingContextExt)
            if naming_context is None:
                with console_lock:
                    print("FAILED: NamingContextExt narrowing returned None")
                sys.exit(1)
            with console_lock:
                print("Step 2: NameService resolved and narrowed")

            auth_obj = naming_context.resolve_str("AuthenticationService")
            auth_service = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
            if auth_service is None:
                with console_lock:
                    print("FAILED: AuthenticationService narrowing returned None")
                sys.exit(1)
            SessionManager.set_auth_service(auth_service)
            with console_lock:
                print("Step 3: AuthenticationService resolved")

            game_obj = naming_context.resolve_str("GameService")
            game_service = game_obj._narrow(GameIDL.GameService)
            if game_service is None:
                with console_lock:
                    print("FAILED: GameService narrowing returned None")
                sys.exit(1)
            SessionManager.set_game_service(game_service)
            with console_lock:
                print("Step 4: GameService resolved")

            break

        except CORBA.TRANSIENT as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Failed to connect to NameService at {server_ip}:1050: {e}")
                print("Possible causes:")
                print("- The server IP address or hostname is incorrect.")
                print("- The server is not running or not listening on port 1050.")
                print("- A network issue (e.g., firewall) is blocking the connection.")
                print("Please verify the server is running and the IP/port are correct, then try again.")
            continue

    login_attempts = 0
    max_login_attempts = 3
    while True:
        with console_lock:
            print("\n--- LOGIN ---")
            print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
        username = input().strip()
        if username.lower() == 'exit':
            with console_lock:
                print("Exiting login client.")
            break

        with console_lock:
            print(f"[CLIENT | {current_time()}] Enter password: ", end='')
        password = input().strip()

        if not username or not password:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Username or password cannot be empty!")
            continue

        if forced_logout_flag.is_set():
            with console_lock:
                print(f"[CLIENT | {current_time()}] Waiting due to recent forced logout. Please try again shortly.")
            forced_logout_flag.clear()
            time.sleep(2)
            continue

        try:
            callback_servant = LoginCallbackServant()
            poa = SessionManager.get_poa()
            callback_ref = register_login_callback(poa, callback_servant)
            token = auth_service.login(username, password, callback_ref)
            player_id = token[1]
            session_token = token[0]
            player_account = PlayerAccount(player_id, username)
            SessionManager.set_session_token((session_token, player_id))
            SessionManager.set_logged_in_player(player_account)
            login_attempts = 0  # Reset attempts on success

            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Login successful!")
                print(f"Token: {token}")

            if forced_logout_flag.is_set():
                forced_logout_flag.clear()
                continue

            while True:
                try:
                    display_menu()
                    choice = non_blocking_input(f"[CLIENT | {current_time()} | {username}] Select an option: ")
                    if choice is None or forced_logout_flag.is_set():
                        forced_logout_flag.clear()
                        break
                    if not choice:
                        continue
                    choice = choice.lower()
                    if choice == "1":
                        if not start_game(game_service, username, token, auth_service):
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
                        return
                    else:
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Invalid choice. Please enter 1, 2, 3, 4, or 'exit'.")
                except Exception as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Error in menu: {e}")
                    continue

        except AuthenticationIDL.AlreadyLoggedInException:
            login_attempts += 1
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Already logged in. Another client may be active. Attempt {login_attempts}/{max_login_attempts}.")
                print("Please ensure only one client is using these credentials.")
            if login_attempts >= max_login_attempts:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Max login attempts reached. Please wait and try again.")
                time.sleep(5)
                login_attempts = 0
            else:
                time.sleep(2)
        except AuthenticationIDL.AuthenticationException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Invalid username or password.")
            login_attempts = 0
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Login failed: {e}")
                print("Please try again or check server status.")
            login_attempts = 0

if __name__ == "__main__":
    main()