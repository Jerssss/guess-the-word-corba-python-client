import sys
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
print(dir(AuthenticationIDL))
import PlayerCallBackIDL

def main():
    orb = CORBA.ORB_init(
        sys.argv + ['-ORBInitRef', 'NameService=corbaloc::localhost:2000/NameService'],
        CORBA.ORB_ID
    )
    print("Step 1: ORB initialized")

    try:
        obj = orb.resolve_initial_references("NameService")
        print("Step 2: NameService resolved")
    except Exception as e:
        print("FAILED at resolve_initial_references:", e)
        sys.exit(1)

    try:
        naming_context = obj._narrow(CosNaming.NamingContextExt)
        if naming_context is None:
            raise RuntimeError("NamingContextExt narrowing returned None")
        print("Step 3: NamingContextExt narrowed")
    except Exception as e:
        print("FAILED at NamingContextExt narrow:", e)
        sys.exit(1)

    try:
        print("Available bindings in Naming Service:")
        binding_list, _ = naming_context.list(100)
        for binding in binding_list:
            name = ".".join([n.id for n in binding.binding_name])
            print(" -", name)
            print("   Object Type:", binding.binding_type)
    except Exception as e:
        print("Could not list bindings:", e)

    try:
        auth_obj = naming_context.resolve_str("AuthenticationService")
        print("Step 4: resolved AuthenticationService object:", auth_obj)
    
        # Narrow immediately using generated stub
        authSvc = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
        print("Expected Repository ID:", AuthenticationIDL.AuthenticationService._NP_RepositoryId)
        if authSvc is None:
            raise RuntimeError("Narrowing failed - repository ID mismatch")
        
        print("Actual Repository ID:", authSvc._repository_id())

    except Exception as e:
        print("FAILED at resolve_str:", e)
        sys.exit(1)

    print("Step 5: Successfully narrowed to AuthenticationService")
    # Check the repository_id of the narrowed object
    print("Repository ID of the narrowed object:", authSvc._repository_id())

    # Use CORBA.LongHolder for out long
    player_id_holder = CORBA.LongHolder()

    # Callback is optional; use None for now
    callback_ref = None

    try:
        token = authSvc.login(
            "seb",              # test username
            "yourpassword",     # test password
            player_id_holder,
            callback_ref
        )
        print(f"[CLIENT] Login successful: Token = {token}, Player ID = {player_id_holder.value}")
    except AuthenticationIDL.AlreadyLoggedInException:
        print("[CLIENT] Already logged in.")
    except AuthenticationIDL.AuthenticationException as e:
        print(f"[CLIENT] Authentication failed: {e}")
    except Exception as e:
        print(f"[CLIENT] Unexpected exception: {e}")

if __name__ == "__main__":
    main()
