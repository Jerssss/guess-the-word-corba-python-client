import threading
import time
from omniORB import CORBA
import GameIDL
import PlayerCallBackIDL__POA
from common import current_time, console_lock, forced_logout_flag
from session import SessionManager

class GameController:
    def __init__(self, game_service, player_id, session_token, game_token):
        self.game_service = game_service
        self.player_id = player_id
        self.session_token = session_token
        self.game_token = game_token
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
        self.rounds_ended = set()
        self.player_wins = {}  # Track wins per player
        self.processed_rounds = set()  # Track processed round callbacks

    def get_setting(self, key):
        server_key = "round_duration" if key == "round_time" else key
        max_retries = 3
        for attempt in range(max_retries):
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Forced logout detected while getting setting '{server_key}'. Aborting.")
                return 60 if key == "round_time" else 10 if key == "countdown_to_game_start" else 0
            try:
                val = self.game_service.getSetting(server_key, self.session_token)
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Got setting '{server_key}' = '{val}' from server")
                if val is None or val.strip() == "":
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] Warning: Setting '{server_key}' is empty or null, using default value.")
                    return 60 if key == "round_time" else 10 if key == "countdown_to_game_start" else 0
                return int(val)
            except ValueError:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Warning: Invalid value '{val}' for setting '{server_key}', using default.")
                return 60 if key == "round_time" else 10 if key == "countdown_to_game_start" else 0
            except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST, CORBA.UNKNOWN) as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] CORBA error getting setting '{server_key}' (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Failed to get setting '{server_key}' after {max_retries} attempts, using default.")
                return 60 if key == "round_time" else 10 if key == "countdown_to_game_start" else 0
            except Exception as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Unexpected error getting setting '{server_key}': {e}")
                return 60 if key == "round_time" else 10 if key == "countdown_to_game_start" else 0

    def handle_round_start(self, round_no):
        # Ignore duplicate or outdated round callbacks
        if round_no <= self.current_round or round_no in self.processed_rounds:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Ignoring duplicate or outdated round {round_no} callback")
            return
        self.processed_rounds.add(round_no)
        self.current_round = round_no

        # Reset round state
        self.secret_word = ""
        self.revealed_word = []
        self.lives = 0
        self.round_time_limit = 0
        self.round_start_time = 0
        self.round_ended.clear()

        with console_lock:
            print(f"[CLIENT | {current_time()}] Initializing round {round_no} with game_token={self.game_token}, session_token={self.session_token}")

        # Check for forced logout before proceeding
        if forced_logout_flag.is_set():
            with console_lock:
                print(f"[CLIENT | {current_time()}] Forced logout detected before starting round {round_no}. Ending round.")
            self.round_ended.set()
            return

        # Attempt to get random word
        try:
            self.secret_word = self.game_service.getRandomWord(self.game_token, round_no, self.player_id, self.session_token)
            if not self.secret_word:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Error: Empty secret word received for round {round_no}. Ending round.")
                self.round_ended.set()
                return

            self.revealed_word = ['_'] * len(self.secret_word)
            self.lives = self.get_setting("number_of_lives")
            self.round_time_limit = self.get_setting("round_time")
            if self.round_time_limit <= 0:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Error: Invalid round time limit {self.round_time_limit}. Using default 60 seconds.")
                self.round_time_limit = 60
            self.round_start_time = time.time()

            with console_lock:
                print(f"\n[CLIENT | {current_time()}] Round {round_no} started!")
                print(f"[CLIENT | {current_time()}] Word to guess: {' '.join(self.revealed_word)}")
                print(f"[CLIENT | {current_time()}] Lives: {self.lives}")
                print(f"[CLIENT | {current_time()}] Time limit: {self.round_time_limit} seconds")
            self.round_started.set()

        except GameIDL.GameNotFoundException as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] GameNotFoundException in round {round_no}: {e}")
                print(f"[CLIENT | {current_time()}] Game state not found. Ending round.")
            self.round_ended.set()
        except GameIDL.NotLoggedInException as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Session invalid during getRandomWord for round {round_no}: {e}")
                print(f"[CLIENT | {current_time()}] Attempting single re-authentication...")
            player = SessionManager.get_logged_in_player()
            if not player or not hasattr(player, 'password'):
                with console_lock:
                    print(f"[CLIENT | {current_time()}] No valid player data for re-authentication. Ending round.")
                self.round_ended.set()
                return
            from login import LoginManager
            login_manager = LoginManager(SessionManager.get_auth_service(), SessionManager.get_poa())
            new_token = login_manager.reauthenticate(player.username, player.password)
            if new_token:
                self.session_token, self.player_id = new_token
                SessionManager.set_session_token(new_token)
                self.game_service = SessionManager.get_game_service()
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Re-authenticated successfully. Retrying getRandomWord...")
                try:
                    self.secret_word = self.game_service.getRandomWord(self.game_token, round_no, self.player_id, self.session_token)
                    if not self.secret_word:
                        with console_lock:
                            print(f"[CLIENT | {current_time()}] Error: Empty secret word after re-auth for round {round_no}. Ending round.")
                        self.round_ended.set()
                        return
                    self.revealed_word = ['_'] * len(self.secret_word)
                    self.lives = self.get_setting("number_of_lives")
                    self.round_time_limit = self.get_setting("round_time")
                    if self.round_time_limit <= 0:
                        with console_lock:
                            print(f"[CLIENT | {current_time()}] Error: Invalid round time limit {self.round_time_limit}. Using default 60 seconds.")
                        self.round_time_limit = 60
                    self.round_start_time = time.time()
                    with console_lock:
                        print(f"\n[CLIENT | {current_time()}] Round {round_no} started after re-auth!")
                        print(f"[CLIENT | {current_time()}] Word to guess: {' '.join(self.revealed_word)}")
                        print(f"[CLIENT | {current_time()}] Lives: {self.lives}")
                        print(f"[CLIENT | {current_time()}] Time limit: {self.round_time_limit} seconds")
                    self.round_started.set()
                except Exception as retry_e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()}] Failed to get word after re-auth: {retry_e}")
                        print(f"[CLIENT | {current_time()}] Please check server logs at 192.168.100.108 for details.")
                    self.round_ended.set()
            else:
                with console_lock:
                    print(f"[CLIENT | {current_time()}] Re-authentication failed. Ending round.")
                self.round_ended.set()
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()}] Unexpected error starting round {round_no}: {e}")
                print(f"[CLIENT | {current_time()}] Please check server logs at 192.168.100.108 for details.")
            self.round_ended.set()

    def play_round(self, username):
        max_guess_retries = 3
        while not self.round_ended.is_set():
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            elapsed_time = time.time() - self.round_start_time
            rem_time = max(0, self.round_time_limit - elapsed_time)
            if rem_time <= 0:
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Time's up! Round over.")
                self.round_ended.set()
                break
            with console_lock:
                print(f"\n[CLIENT | {current_time()} | {username}] Word: {' '.join(self.revealed_word)}")
                print(f"[CLIENT | {current_time()} | {username}] Lives: {self.lives}")
                print(f"[CLIENT | {current_time()} | {username}] Time remaining: {int(rem_time)} seconds")
                print(f"[CLIENT | {current_time()} | {username}] Enter a letter (or 'quit' to leave): ", end='', flush=True)
            guess = input().strip().upper()
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"\n[CLIENT | {current_time()} | {username}] Session invalidated. Returning to login.")
                self.round_ended.set()
                break
            if guess.lower() == 'quit':
                try:
                    self.game_service.leaveLobby(self.player_id, self.game_token, self.session_token)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Successfully left the game lobby.")
                    self.game_ended.set()
                    self.round_ended.set()
                    return
                except Exception as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Error leaving lobby: {e}")
                    self.game_ended.set()
                    self.round_ended.set()
                    return
            if len(guess) != 1 or not guess.isalpha():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid input. Please enter a single letter.")
                continue
            for attempt in range(max_guess_retries):
                if forced_logout_flag.is_set():
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Session invalidated during guess. Returning to login.")
                    self.round_ended.set()
                    break
                try:
                    guess_time = int(time.time())  # Current Unix timestamp in seconds
                    positions = self.game_service.guessLetter(self.game_token, self.player_id, self.session_token, guess[0], guess_time)
                    if positions:
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
                    break  # Success, exit retry loop
                except GameIDL.AlreadyGuessedLetterException:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Letter '{guess}' was already guessed. Try a different letter.")
                    break
                except GameIDL.MaxAttemptsReachedException:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Maximum attempts reached. Round over.")
                    self.round_ended.set()
                    break
                except GameIDL.NotLoggedInException as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Session invalid during guess (attempt {attempt + 1}/{max_guess_retries}): {e}")
                    player = SessionManager.get_logged_in_player()
                    if not player:
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] No player data available. Ending round.")
                        self.round_ended.set()
                        break
                    from login import LoginManager
                    login_manager = LoginManager(SessionManager.get_auth_service(), SessionManager.get_poa())
                    new_token = login_manager.reauthenticate(player.username, player.password)
                    if new_token:
                        self.session_token, self.player_id = new_token
                        self.game_service = SessionManager.get_game_service()
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] Re-authenticated successfully for guess. Please try again.")
                        continue
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Re-authentication failed. Ending round.")
                    self.round_ended.set()
                    break
                except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST, CORBA.UNKNOWN) as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] CORBA error during guess (attempt {attempt + 1}/{max_guess_retries}): {e}")
                    if attempt < max_guess_retries - 1:
                        time.sleep(1)
                        continue
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Failed to process guess after {max_guess_retries} attempts. Ending round.")
                    self.round_ended.set()
                    break
                except Exception as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Unexpected error during guess: {e}")
                        print(f"[CLIENT | {current_time()} | {username}] Please check server logs at 192.168.100.108 for details.")
                    self.round_ended.set()
                    break

    def handle_round_end(self, winner_name, secret_word):
        if self.current_round in self.rounds_ended:
            return
        self.rounds_ended.add(self.current_round)
        self.winner_name = winner_name if winner_name and winner_name.strip() else "Nobody"
        self.secret_word = secret_word  # Sync with server's secretWord
        if self.winner_name != "Nobody":
            self.player_wins[self.winner_name] = self.player_wins.get(self.winner_name, 0) + 1
        self.round_ended.set()
        with console_lock:
            print(f"\nRound {self.current_round} ended. Winner: {self.winner_name}, Secret word: {secret_word}")
            print("Current win counts:")
            if self.player_wins:
                for player, wins in self.player_wins.items():
                    print(f"  {player}: {wins} win{'s' if wins != 1 else ''}")
            else:
                print("  No wins recorded yet.")
            print("Waiting for the next round...")

    def handle_game_end(self, winner_name):
        self.champion = winner_name if winner_name and winner_name.strip() else "Nobody"
        self.game_ended.set()
        with console_lock:
            print(f"\nGame ended. Overall winner: {self.champion}")
            print("Final win counts:")
            if self.player_wins:
                for player, wins in self.player_wins.items():
                    print(f"  {player}: {wins} win{'s' if wins != 1 else ''}")
            else:
                print("  No wins recorded.")
            print("Returning to lobby...")

class GameCallbackServant(PlayerCallBackIDL__POA.GameCallBackService):
    def __init__(self, controller):
        self.controller = controller

    def notifyGameStart(self, gameToken, sessionToken):
        if self.controller.game_ended.is_set():
            return  # Ignore callback if game has ended
        with console_lock:
            print(f"\n[Callback] Game started with token {gameToken}")

    def notifyRoundStart(self, gameToken, roundNumber, sessionToken):
        if self.controller.game_ended.is_set():
            return  # Ignore callback if game has ended
        with console_lock:
            print(f"\n[Callback] Round {roundNumber} started with gameToken={gameToken}, sessionToken={sessionToken}")
        self.controller.handle_round_start(roundNumber)

    def notifyRoundEnd(self, gameToken, sessionToken, winnerName, secretWord):
        if self.controller.game_ended.is_set():
            return  # Ignore callback if game has ended
        with console_lock:
            print(f"\n[Callback] Round ended. Winner: {winnerName}, Word: {secretWord}")
        self.controller.handle_round_end(winnerName, secretWord)

    def notifyGameEnd(self, gameToken, sessionToken, winnerName):
        if self.controller.game_ended.is_set():
            return  # Ignore callback if game has ended
        with console_lock:
            print(f"\n[Callback] Game ended. Winner: {winnerName}")
        self.controller.handle_game_end(winnerName)

class GameManager:
    def __init__(self, game_service, auth_service, poa):
        self.game_service = game_service
        self.auth_service = auth_service
        self.poa = poa
        self.reauth_attempts = 0
        self.max_reauth_attempts = 3

    def register_game_callback(self, callback_servant):
        return self.poa.servant_to_reference(callback_servant)

    def start_game(self, username, token):
        session_token, player_id = token
        self.reauth_attempts = 0
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Starting a new game...")
            print(f"[CLIENT | {current_time()} | {username}] Joining the waiting room...")

        try:
            if not SessionManager.get_session_token():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Session token invalid. Please log in again.")
                return False

            time.sleep(0.5)
            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Forced logout detected before joining lobby. Returning to login.")
                return False
            try:
                game_token = self.game_service.joinLobby(player_id, session_token)
            except GameIDL.NotLoggedInException as e:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Session invalid during joinLobby: {e}")
                    print(f"[CLIENT | {current_time()} | {username}] Please log in again.")
                return False
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Joined waiting room: {game_token}")

            controller = GameController(self.game_service, player_id, session_token, game_token)
            lobby_wait_time = controller.get_setting("countdown_to_game_start")
            player_count = 0
            for remaining in range(lobby_wait_time, -1, -1):
                if forced_logout_flag.is_set():
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Forced logout detected. Returning to login.")
                    return False
                try:
                    player_count = self.game_service.getNumberOfPlayersJoined(player_id, session_token)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
                except GameIDL.NotLoggedInException as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Session invalid during getNumberOfPlayersJoined: {e}")
                        print(f"[CLIENT | {current_time()} | {username}] Please log in again.")
                    return False
                except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST, CORBA.UNKNOWN) as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] CORBA error during getNumberOfPlayersJoined: {e}")
                        print(f"[CLIENT | {current_time()} | {username}] Please check server logs at 192.168.100.108 for details.")
                    return False
                time.sleep(2)  # Increased interval to reduce server load
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Countdown finished. Current players: {player_count}")
                if player_count < 2:
                    print(f"[CLIENT | {current_time()} | {username}] Not enough players joined within {lobby_wait_time} seconds. Returning to home screen.")
                    return True
                print(f"[CLIENT | {current_time()} | {username}] Enough players joined! Starting game...")

            if forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Forced logout detected before starting round. Returning to login.")
                return False

            callback_servant = GameCallbackServant(controller)
            callback_ref = self.register_game_callback(callback_servant)
            self.game_service.registerCallBack(player_id, game_token, session_token, callback_ref)

            self.game_service.startRound(game_token, 1, player_id, session_token)

            while not controller.game_ended.is_set() and not forced_logout_flag.is_set():
                if not controller.round_started.wait(timeout=30):
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to start. Exiting game.")
                    break
                controller.round_started.clear()
                controller.play_round(username)
                if not controller.round_ended.wait(timeout=15):
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to end. Checking game status...")
                    if controller.game_ended.is_set():
                        break
                controller.round_ended.clear()
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Round {controller.current_round} ended. Winner: {controller.winner_name}, Word: {controller.secret_word}")

            if not controller.game_ended.is_set() and not forced_logout_flag.is_set():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Waiting for game to officially end...")
                if not controller.game_ended.wait(timeout=60):
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for game to end. Forcing exit.")
                else:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Game ended. Overall winner: {controller.champion}")
            else:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Game ended. Overall winner: {controller.champion}")

            return True

        except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST, CORBA.UNKNOWN) as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] CORBA error during game: {e}")
                print(f"[CLIENT | {current_time()} | {username}] Please check server logs at 192.168.100.108 for details.")
            return False
        except GameIDL.NotEnoughPlayersException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Not enough players to start the game after waiting.")
            return True
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Unexpected error during game: {e}")
                print(f"[CLIENT | {current_time()} | {username}] Please check server logs at 192.168.100.108 for details.")
            return False