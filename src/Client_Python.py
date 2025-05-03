import sys
import time
from omniORB import CORBA
from PlayerCallBackIDL import LoginCallbackService, WaitingRoomGameCallbackService, GameCallBackService
from GameIDL import GameService
from AuthenticationIDL import AuthenticationService

class LoginCallbackServiceImpl(LoginCallbackService):
    def notifyForcedLogout(self, playerID, sessionToken):
        print(f"[Callback] Forced logout received for player {playerID}")
        print("You have been logged out because you signed in elsewhere.")
        sys.exit(0)

class WaitingRoomGameCallbackServiceImpl(WaitingRoomGameCallbackService):
    def notifyPlayerJoined(self, gameToken, totalPlayers, sessionToken):
        print(f"[WaitingRoom] Player joined. Total players: {totalPlayers}")

    def notifyCountdownStart(self, gameToken, countdownSeconds, sessionToken):
        print(f"[WaitingRoom] Countdown started: {countdownSeconds} seconds")
        for i in range(countdownSeconds, 0, -1):
            print(f"[WaitingRoom] Time remaining: {i} seconds")
            time.sleep(1)

    def notifyCountdownReset(self, gameToken, sessionToken):
        print("[WaitingRoom] Countdown reset.")

class GameCallBackServiceImpl(GameCallBackService):
    def notifyGameStart(self, gameToken, sessionToken):
        print("[Game] The game has started!")

    def notifyRoundStart(self, gameToken, roundNumber, sessionToken):
        print(f"[Game] Round {roundNumber} has started!")

    def notifyRoundEnd(self, gameToken, sessionToken, result):
        print(f"[Game] Round ended. Result: {result}")

    def notifyGameEnd(self, gameToken, sessionToken, result):
        print(f"[Game] Game ended. Result: {result}")
        sys.exit(0)

class GameClient:
    def __init__(self, orb):
        self.orb = orb
        self.sessionToken = None
        self.playerID = None
        self.gameService = None
        self.authService = None

    def connect(self):
        # Resolve the naming service
        obj = self.orb.resolve_initial_references("NameService")
        rootContext = NamingContextExtHelper.narrow(obj)

        # Get references to the services
        self.authService = AuthenticationServiceHelper.narrow(rootContext.resolve("AuthenticationService"))
        self.gameService = GameServiceHelper.narrow(rootContext.resolve("GameService"))

    def login(self, username, password):
        callback = LoginCallbackServiceImpl()
        playerIDHolder = CORBA.IntHolder()
        self.sessionToken = self.authService.login(username, password, playerIDHolder, callback)
        self.playerID = playerIDHolder.value
        print(f"[Client] Logged in as {username}. Session Token: {self.sessionToken}")

    def join_lobby(self):
        gameToken = self.gameService.joinLobby(self.playerID, self.sessionToken)
        print(f"[Client] Joined lobby with token: {gameToken}")
        return gameToken

    def leave_lobby(self, gameToken):
        self.gameService.leaveLobby(self.playerID, gameToken, self.sessionToken)
        print("[Client] Left the lobby.")

    def start_game(self):
        # Implement game logic here
        pass

if __name__ == "__main__":
    # Initialize the ORB
    orb = CORBA.ORB_init(sys.argv)
    client = GameClient(orb)

    try:
        client.connect()
        username = input("Enter username: ")
        password = input("Enter password: ")
        client.login(username, password)

        gameToken = client.join_lobby()
        # Here you can implement further game logic, such as waiting for game events
        # and handling user input for guessing letters, etc.

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        client.orb.shutdown()
