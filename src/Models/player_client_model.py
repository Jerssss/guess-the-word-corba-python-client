import sys
import omniORB
from omniORB import CORBA, PortableServer
import CosNaming

# Import the IDL files that were compiled by omniidl
from Idls.AuthenticationIDL import AuthenticationIDL_idl
from Idls.GameIDL import GameIDL_idl
from Services.session_manager import SessionManager

class PlayerClient_Model:
    def __init__(self, orb_args):
        # ORB & POA initialization
        self.orb = CORBA.ORB_init(orb_args, CORBA.ORB_ID)
        self.root_poa = self.orb.resolve_initial_references("RootPOA")
        self.root_poa = self.root_poa._narrow(PortableServer.POA)
        self.root_poa._get_the_POAManager().activate()
        SessionManager.init_orb(self.orb, self.root_poa)

        # NameService lookup
        naming_service = self.orb.resolve_initial_references("NameService")
        naming_context = naming_service._narrow(CosNaming.NamingContextExt)

        # Resolve AuthenticationService
        obj = naming_context.resolve_str("AuthenticationService")
        self.auth_service = obj._narrow(AuthenticationIDL_idl.AuthenticationService)

        # Resolve GameService
        self.game_service = GameIDL_idl.GameServiceHelper.narrow(
            naming_context.resolve_str("GameService")
        )
        SessionManager.set_game_service(self.game_service)

    def get_auth_service(self):
        return self.auth_service

    def get_game_service(self):
        return self.game_service

    def start_orb(self):
        # Start the ORB event loop in a separate thread
        import threading
        threading.Thread(target=self.orb.run).start()

    def register_login_callback(self, callback_servant):
        try:
            ref = self.root_poa.servant_to_reference(callback_servant)
            return AuthenticationIDL_idl.LoginCallbackServiceHelper.narrow(ref)
        except Exception as e:
            raise RuntimeError("Login callback registration failed") from e

    def register_game_callback(self, callback_servant):
        try:
            ref = self.root_poa.servant_to_reference(callback_servant)
            return GameIDL_idl.GameCallBackServiceHelper.narrow(ref)
        except Exception as e:
            raise RuntimeError("Game callback registration failed") from e

    def register_waiting_room_callback(self, callback_servant):
        try:
            ref = self.root_poa.servant_to_reference(callback_servant)
            return GameIDL_idl.WaitingRoomGameCallbackServiceHelper.narrow(ref)
        except Exception as e:
            raise RuntimeError("Waiting-room callback registration failed") from e
