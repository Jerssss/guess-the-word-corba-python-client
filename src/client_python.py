import sys
from omniORB import CORBA
import CosNaming
from Idls import AuthenticationIDL_idl, PlayerCallBackIDL_idl  # Include both IDL modules

def main():
    orb = CORBA.ORB_init(
        sys.argv + ['-ORBInitRef', 'NameService=corbaloc::localhost:1050/NameService'],
        CORBA.ORB_ID
    )
    print("ORB object:", orb)
    print("Step 1 completed successfully")

    try:
        obj = orb.resolve_initial_references("NameService")
        print("Step 2: resolve_initial_references succeeded")
    except Exception as e:
        print("FAILED at resolve_initial_references:", e)
        sys.exit(1)

    try:
        naming_context = obj._narrow(CosNaming.NamingContextExt)
        print("Step 3: narrowed to NamingContextExt")
        if naming_context is None:
            raise RuntimeError("narrow->NamingContextExt returned None")
    except Exception as e:
        print("FAILED at NamingContextExt narrow:", e)
        sys.exit(1)

    try:
        print("Listing all bindings in the Naming Service...")
        binding_list, _ = naming_context.list(100)
        for binding in binding_list:
            name = ".".join([n.id for n in binding.binding_name])
            print(" - Found name:", name)
    except Exception as e:
        print("Could not list bindings:", e)

    try:
        auth_obj = naming_context.resolve_str("AuthenticationService")
        print("Step 4: resolved authObj:", auth_obj)
    except Exception as e:
        print("FAILED at resolve_str:", e)
        sys.exit(1)

    try:
        auth_obj = naming_context.resolve_str("AuthenticationService")
        print("Step 4: resolved authObj:", auth_obj)
        print("Type of resolved object:", type(auth_obj))  # Debugging line
    except Exception as e:
        print("FAILED at resolve_str:", e)
    sys.exit(1)
    authSvc = auth_obj._narrow(
    AuthenticationIDL_idl._0_AuthenticationIDL._objref_AuthenticationService
    )
    if authSvc is None:
        print("FAILED: object is not AuthenticationService")
    sys.exit(1)

    print("Successfully connected to AuthenticationService")

    # === Step 4: Attempt login ===
    # Assuming you have a direct reference to the AuthenticationService
authSvc = AuthenticationServiceHelper.narrow(auth_obj)

if authSvc is None:
    print("Failed to narrow AuthenticationService")
else:
    print("Successfully narrowed AuthenticationService")
    # Call a method to test
    try:
        player_id_holder = AuthenticationIDL_idl._0_AuthenticationIDL.IntHolder()
        token = authSvc.login("test_user", "test_password", player_id_holder, None)
        print(f"Login successful: Token = {token}, Player ID = {player_id_holder.value}")
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    main()
