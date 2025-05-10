# common.py
import threading
from datetime import datetime

console_lock = threading.Lock()
forced_logout_flag = threading.Event()

def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")