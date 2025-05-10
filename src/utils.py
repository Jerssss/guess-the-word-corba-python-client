import re
from about import About
from common import console_lock, forced_logout_flag

def display_menu():
    print("\n=== Game Lobby ===")
    print("1. Start Game")
    print("2. View Leaderboard")
    print("3. About")
    print("4. Quit")
    print("(Type 'exit' to exit the client)")

def is_valid_ip_or_hostname(address):
    if not address:
        return True
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if re.match(ipv4_pattern, address):
        return True
    hostname_pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+$'
    if re.match(hostname_pattern, address) or address == "localhost":
        return True
    return False

def non_blocking_input(prompt):
    from common import current_time
    with console_lock:
        print(prompt, end='', flush=True)
    choice = input().strip()
    if forced_logout_flag.is_set():
        with console_lock:
            print(f"[CLIENT | {current_time()}] Forced logout detected. Checking session validity...")
        return None
    return choice

def about():
    about_info = About()
    about_info.display()