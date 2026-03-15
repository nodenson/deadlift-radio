import sys
import time
import threading


def grimdark_spinner(message: str, stop_event) -> None:
    symbols = ["[☠]", "[⚙]", "[✠]", "[☢]"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r+++ {message} +++ {symbols[i % len(symbols)]}")
        sys.stdout.flush()
        time.sleep(0.12)
        i += 1
    sys.stdout.write("\r" + " " * (len(message) + 25) + "\r")
    sys.stdout.flush()


def run_with_grimdark_spinner(message: str, fn, *args, **kwargs):
    stop_event = threading.Event()
    thread = threading.Thread(target=grimdark_spinner, args=(message, stop_event))
    thread.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop_event.set()
        thread.join()