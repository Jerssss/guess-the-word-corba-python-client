import sys
from omniORB import CORBA
import CosNaming
import AuthenticationIDL

# Login method is intended to be on the server side, but for testing we simulate it here
def login(self, username, password, callback_ref):
    print(f"Login attempt for user: {username}, password: {password}")
    # Your authentication logic here
    if username == "seb" and password == "password123":
        # Simulate successful login by returning a token value
        return "some_token_value"
    else:
        raise AuthenticationIDL.AuthenticationException("Invalid credentials")

def main():
    orb = CORBA.ORB_init(
        sys.argv + ['-ORBInitRef', 'NameService=corbaloc::localhost:1050/NameService'],
        CORBA.ORB_ID
    )
    print("Step 1: ORB initialized")

    # Step 2: Resolve the NameService
    try:
        obj = orb.resolve_initial_references("NameService")
        print("Step 2: NameService resolved")
    except Exception as e:
        print("FAILED at resolve_initial_references:", e)
        sys.exit(1)

    # Step 3: Narrow the object reference to NamingContextExt
    try:
        naming_context = obj._narrow(CosNaming.NamingContextExt)
        if naming_context is None:
            raise RuntimeError("NamingContextExt narrowing returned None")
        print("Step 3: NamingContextExt narrowed")
    except Exception as e:
        print("FAILED at NamingContextExt narrow:", e)
        sys.exit(1)

    # Step 4: List available bindings in the Naming Service
    try:
        print("Available bindings in Naming Service:")
        binding_list, _ = naming_context.list(100)
        for binding in binding_list:
            name = ".".join([n.id for n in binding.binding_name])
            print(f" - {name}")
            print(f"   Object Type: {binding.binding_type}")
    except Exception as e:
        print("Could not list bindings:", e)

    # Step 5: Resolve the AuthenticationService object
    try:
        auth_obj = naming_context.resolve_str("AuthenticationService")
        print("Step 5: resolved AuthenticationService object:", auth_obj)

        # Narrow the resolved object to the AuthenticationService type
        authSvc = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
        if authSvc is None:
            raise RuntimeError("Narrowing failed - object is not of type AuthenticationService")

        print("Step 6: Successfully narrowed to AuthenticationService")
    except Exception as e:
        print("FAILED at resolve_str:", e)
        sys.exit(1)

    # Callback reference is optional, set to None for now
    callback_ref = None

    # Step 6: Attempt to log in with correct credentials
    try:
        token = authSvc.login("1", "1", callback_ref)
        print(f"[CLIENT] Login successful: Token = {token}")
    except AuthenticationIDL.AlreadyLoggedInException:
        print("[CLIENT] Already logged in.")
    except AuthenticationIDL.AuthenticationException as e:
        # Print the exception message and other details
        print(f"[CLIENT] Authentication failed: {str(e)}")  # Print the string representation of the exception
        if hasattr(e, 'message'):
            print(f"[CLIENT] Exception Message: {e.message}")  # More detailed exception info
    except Exception as e:
        # Catch any unexpected exceptions
        print(f"[CLIENT] Unexpected exception: {e}")

if __name__ == "__main__":
    main()
