import sys
import threading
import traceback


def print_stacktrace() -> None:
    stacktrace = ""
    for thread in threading.enumerate():
        assert thread.ident is not None
        stacktrace += str(thread)
        stacktrace += "".join(
            traceback.format_stack(sys._current_frames()[thread.ident])
        )
    print(f"stacktrace: {stacktrace}")


def print_thread_name() -> None:
    print(f"thread name: {threading.current_thread().name}")
