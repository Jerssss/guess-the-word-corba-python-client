import sys
from omniORB import CORBA
import CosNaming
import AuthenticationIDL
from datetime import datetime

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def display_menu():
    print("\n=== Main Menu ===")
    print("1. Start Game")
    print("2. View Leaderboard")
    print("3. About")
    print("4. Quit")

def start_game():
    print(f"[CLIENT | {current_time()}] Starting a new game...")

def view_leaderboard():
    print(f"[CLIENT | {current_time()}] Displaying leaderboard...")

def about():
    print(f"[CLIENT | {current_time()}] This is the game client, built using CORBA.")

def main():
    # Ask user for the IP address to connect to
    print(f"[CLIENT | {current_time()}] Enter server IP address (or press Enter for default 'localhost'): ", end='')
    server_ip = input().strip()
    if not server_ip:
        server_ip = "localhost"

    # Initialize the ORB with the provided IP
    orb = CORBA.ORB_init(
        sys.argv + [f'-ORBInitRef', f'NameService=corbaloc::{server_ip}:1050/NameService'],
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

    callback_ref = None
    while True:
        print("\n--- LOGIN ---")
        print(f"[CLIENT | {current_time()}] Enter username (or type 'exit' to quit): ", end='')
        username = input().strip()
        if username.lower() == 'exit':
            print("Exiting login client.")
            return

        print(f"[CLIENT | {current_time()}] Enter password: ", end='')
        password = input().strip()

        try:
            token = authSvc.login(username, password, callback_ref)
            print(f"[CLIENT | {current_time()} | {username}] Login successful!")
            print(f"Token: {token}")

            # Post-login menu
            while True:
                display_menu()
                choice = input(f"[CLIENT | {current_time()} | {username}] Select an option to choose: ").strip()

                if choice == "1":
                    start_game()
                elif choice == "2":
                    view_leaderboard()
                elif choice == "3":
                    about()
                elif choice == "4":
                    print(f"[CLIENT | {current_time()}] Quitting...")
                    return
                else:
                    print(f"[CLIENT | {current_time()}] Invalid choice. Please try again.")
                    
        except AuthenticationIDL.AlreadyLoggedInException:
            print(f"[CLIENT | {current_time()} | {username}] Already logged in.")
            return
        except AuthenticationIDL.AuthenticationException:
            print(f"[CLIENT | {current_time()}] Invalid username or password.")
        except Exception as e:
            print(f"[CLIENT | {current_time()}] Unexpected error: {e}")

if __name__ == "__main__":
    main()
