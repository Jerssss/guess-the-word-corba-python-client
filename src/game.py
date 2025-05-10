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
        self.rounds_ended = set()

    def get_setting(self, key):
        try:
            val = self.game_service.getSetting(key, self.session_token)
            if not val:
                with console_lock:
                    print(f"Warning: Setting {key} is empty, using default value.")
                return 60 if key == "round_time" else 0
            return int(val)
        except ValueError:
            with console_lock:
                print(f"Warning: Invalid {key} value, using default.")
            return 60 if key == "round_time" else 0
        except Exception as e:
            with console_lock:
                print(f"Warning: Error getting setting {key}: {e}, using default.")
            return 60 if key == "round_time" else 0

    def handle_round_start(self, round_no):
        if self.current_round == round_no:
            return
        self.current_round = round_no
        try:
            self.secret_word = self.game_service.getRandomWord(self.game_token, round_no, self.player_id, self.session_token)
            if not self.secret_word:
                with console_lock:
                    print(f"Error: Empty secret word received for round {round_no}.")
                self.round_ended.set()
                return
            self.revealed_word = ['_'] * len(self.secret_word)
            self.lives = self.get_setting("number_of_lives")
            self.round_time_limit = self.get_setting("round_time")
            if self.round_time_limit <= 0:
                with console_lock:
                    print(f"Error: Invalid round time limit {self.round_time_limit}. Ending round.")
                self.round_ended.set()
                return
            self.round_start_time = time.time()
            self.round_ended.clear()
            with console_lock:
                print(f"\nRound {round_no} started!")
                print(f"Word to guess: {' '.join(self.revealed_word)}")
                print(f"Lives: {self.lives}")
                print(f"Time limit: {self.round_time_limit} seconds")
            self.round_started.set()
        except Exception as e:
            with console_lock:
                print(f"Error starting round {round_no}: {e}")
            self.round_ended.set()

    def play_round(self, username):
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
            if guess == 'QUIT':
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Quitting the round...")
                self.round_ended.set()
                break
            if len(guess) != 1 or not guess.isalpha():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Invalid input. Please enter a single letter.")
                continue
            try:
                positions = self.game_service.guessLetter(self.game_token, self.player_id, self.session_token, guess)
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
                self.round_ended.set()
                break

    def handle_round_end(self, winner_name, secret_word):
        if self.current_round in self.rounds_ended:
            return
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

class GameManager:
    def __init__(self, game_service, auth_service, poa):
        self.game_service = game_service
        self.auth_service = auth_service
        self.poa = poa

    def register_game_callback(self, callback_servant):
        return self.poa.servant_to_reference(callback_servant)

    def start_game(self, username, token):
        session_token, player_id = token
        with console_lock:
            print(f"[CLIENT | {current_time()} | {username}] Starting a new game...")
            print(f"[CLIENT | {current_time()} | {username}] Joining the waiting room...")

        try:
            if not SessionManager.get_session_token():
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] Session token invalid. Please log in again.")
                return False

            time.sleep(0.5)
            game_token = self.game_service.joinLobby(player_id, session_token)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Joined waiting room: {game_token}")

            player_count = 0
            for remaining in range(10, -1, -1):
                try:
                    player_count = self.game_service.getNumberOfPlayersJoined(player_id, session_token)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
                except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Server disconnected during lobby: {e}")
                    player = SessionManager.get_logged_in_player()
                    if not player:
                        with console_lock:
                            print(f"[CLIENT | {current_time()} | {username}] No player data available. Returning to login.")
                        return False
                    from connection import reconnect_to_server
                    new_token = reconnect_to_server(SessionManager.get_server_ip(), username, player.password, token)
                    if not new_token:
                        return False
                    token = new_token
                    session_token, player_id = token
                    self.game_service = SessionManager.get_game_service()
                    self.auth_service = SessionManager.get_auth_service()
                    game_token = self.game_service.joinLobby(player_id, session_token)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Rejoined waiting room: {game_token}")
                    player_count = self.game_service.getNumberOfPlayersJoined(player_id, session_token)
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Waiting for players... {remaining} seconds left, current players: {player_count}")
                time.sleep(1)
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Countdown finished. Current players: {player_count}")
                if player_count < 2:
                    print(f"[CLIENT | {current_time()} | {username}] Not enough players joined within 10 seconds. Returning to home screen.")
                    return True
                print(f"[CLIENT | {current_time()} | {username}] Enough players joined! Starting game...")

            controller = GameController(self.game_service, player_id, session_token, game_token)
            callback_servant = GameCallbackServant(controller)
            callback_ref = self.register_game_callback(callback_servant)
            self.game_service.registerCallBack(player_id, game_token, session_token, callback_ref)

            self.game_service.startRound(game_token, 1, player_id, session_token)

            while controller.current_round <= controller.total_rounds and not controller.game_ended.is_set() and not forced_logout_flag.is_set():
                if not controller.round_started.wait(timeout=30):
                    with console_lock:
                        print(f"[CLIENT | {current_time()} | {username}] Timeout waiting for round {controller.current_round} to start. Exiting game.")
                    break
                controller.round_started.clear()
                controller.play_round(username)
                if controller.current_round >= controller.total_rounds:
                    break
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

        except (CORBA.COMM_FAILURE, CORBA.TRANSIENT, CORBA.OBJECT_NOT_EXIST) as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Server disconnected during game: {e}")
            player = SessionManager.get_logged_in_player()
            if not player:
                with console_lock:
                    print(f"[CLIENT | {current_time()} | {username}] No player data available. Returning to login.")
                return False
            from connection import reconnect_to_server
            new_token = reconnect_to_server(SessionManager.get_server_ip(), username, player.password, token)
            if not new_token:
                return False
            return self.start_game(username, new_token)

        except GameIDL.NotLoggedInException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Session invalid (NotLoggedInException). Attempting to re-authenticate...")
            from login import LoginManager
            login_manager = LoginManager(self.auth_service, self.poa)
            new_token = login_manager.reauthenticate(username, SessionManager.get_logged_in_player().password)
            if new_token:
                return self.start_game(username, new_token)
            return False
        except GameIDL.NotEnoughPlayersException:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Not enough players to start the game after waiting.")
            return True
        except Exception as e:
            with console_lock:
                print(f"[CLIENT | {current_time()} | {username}] Error during game: {e}")
            return True