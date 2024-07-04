import json
import sys
import threading
import traceback
from pathlib import Path
from typing import Any


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


def save_to_json_file(file_path: Path, _dict: dict[Any, Any]) -> None:
    """Changes the file extension to .json and saves it"""
    json_file: Path = file_path.with_suffix(".json")

    with json_file.open("w", encoding="utf-8") as file:
        json.dump(_dict, file, ensure_ascii=False, indent=4)


def load_dict_from_json_file(file_path: Path) -> dict[Any, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        dict_from_file = json.load(file)
        assert isinstance(dict_from_file, dict)
        return dict_from_file
