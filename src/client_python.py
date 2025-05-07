import sys
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
from datetime import datetime

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    orb = CORBA.ORB_init(
        sys.argv + ['-ORBInitRef', 'NameService=corbaloc::192.168.12.201:1050/NameService'], # Change the ip here to match the ip of the server
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
        auth_obj = naming_context.resolve_str("AuthenticationService")
        authSvc = auth_obj._narrow(AuthenticationIDL.AuthenticationService)
        if authSvc is None:
            raise RuntimeError("Narrowing failed - object is not of type AuthenticationService")
        print("Step 4: Successfully resolved and narrowed AuthenticationService")
    except Exception as e:
        print("FAILED at resolve_str or narrowing:", e)
        sys.exit(1)

    callback_ref = None  # TODO: callback implementation yet
    while True:
        print("\n--- LOGIN ---")
        print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
        username = input().strip()
        if username.lower() == 'exit':
            print("Exiting login client.")
            break

        print(f"[CLIENT | {current_time()}] Enter password: ", end='')
        password = input().strip()

        try:
            token = authSvc.login(username, password, callback_ref)
            print(f"[CLIENT | {current_time()} | {username}] Login successful!")
            print(f"Token: {token}")
            break  # Exit loop on successful login
        except AuthenticationIDL.AlreadyLoggedInException:
            print(f"[CLIENT | {current_time()} | {username}] Already logged in.")
            break
        except AuthenticationIDL.AuthenticationException:
            print(f"[CLIENT | {current_time()}] Invalid username or password.")
        except Exception as e:
            print(f"[CLIENT | {current_time()}] Unexpected error: {e}")

if __name__ == "__main__":
    main()
