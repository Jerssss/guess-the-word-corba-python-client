import re
import sys
import time
if sys.platform == "win32":
    import msvcrt
else:
    import select
from about import About
from common import console_lock, forced_logout_flag, current_time

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
    with console_lock:
        print(prompt, end='', flush=True)
    while True:
        if forced_logout_flag.is_set():
            forced_logout_flag.clear()
            return 'forced_logout'
        if sys.platform == "win32":
            if msvcrt.kbhit():
                choice = input().strip()
                return choice
            time.sleep(0.1)  # Short sleep to prevent busy-waiting
        else:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)  # 0.1-second timeout
            if rlist:
                choice = sys.stdin.readline().strip()
                return choice

def about():
    about_info = About()
    about_info.display()