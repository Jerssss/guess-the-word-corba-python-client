# File: client_python.py

import sys
import omniORB
from omniORB import CORBA

# Import the IDL files compiled by omniidl
from Idls.GameIDL import GameIDL_idl
from Idls.AuthenticationIDL import AuthenticationIDL_idl

from Shared_Files.player_account import PlayerAccount
from Controllers.game_lobby_controller import GameLobbyController
from Controllers.game_room_controller import GameRoomController
from Controllers.login_controller import LogInController
from Models.login_page_model import LogInPageModel
from Services.session_manager import SessionManager
from Services.login_callback_service import LoginCallBackServiceImpl
from Models.player_client_model import PlayerClient_Model

# Ensure ORBInitRef is set
if "-ORBInitRef" not in " ".join(sys.argv):
    sys.argv += ["-ORBInitRef", "NameService=corbaloc:iiop:192.168.1.101:2000/NameService"]

def main():
    # Initialize client-side ORB and services
    player_client_model = PlayerClient_Model(sys.argv)
    player_client_model.start_orb()

    # Register callback service
    login_callback_servant = LoginCallBackServiceImpl()
    callback_stub = player_client_model.register_login_callback(login_callback_servant)

    # Set up login flow
    auth_service = player_client_model.get_auth_service()
    login_page_model = LogInPageModel(auth_service)
    login_controller = LogInController(login_page_model, callback_stub)

    username = input("Enter username: ")
    password = input("Enter password: ")
    login_controller.on_continue(username, password)

    session_token = SessionManager.get_session_token()
    print(f"Logged in with session token: {session_token}")

    # Simulate a player
    player_account = PlayerAccount(1, username, password, 100)
    SessionManager.set_logged_in_player(player_account)

    # Lobby and Game interaction
    game_service = player_client_model.get_game_service()
    game_lobby_controller = GameLobbyController(game_service)
    game_room_controller = GameRoomController(game_service, SessionManager)

    game_token = game_lobby_controller.join_lobby(player_account, session_token)
    SessionManager.set_game_token(game_token)
    print(f"Joined game lobby with game token: {game_token}")

    round_number = 1
    game_room_controller.start_round(round_number)
    print(f"Started round {round_number} in the game.")

    game_room_controller.guess_letter('A')
    print("Player guessed the letter 'A'.")

    winner = game_room_controller.get_round_winner()
    print(f"The winner of the round is: {winner}")


if __name__ == "__main__":
    main()