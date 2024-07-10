import json
import os
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
    """Changes the file extension to .json and outputs to that location"""
    json_file: Path = file_path.with_suffix(".json")

    with json_file.open("w", encoding="utf-8") as file:
        json.dump(_dict, file, ensure_ascii=False, indent=4)


def load_dict_from_json_file(file_path: Path) -> dict[Any, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        dict_from_file = json.load(file)
        assert isinstance(dict_from_file, dict)
        return dict_from_file


def print_current_directory() -> None:
    print(f"Current Directory: {Path.cwd()}")


def print_directory_tree(root_dir: str, indent: str = "") -> None:
    """
    Print the directory tree rooted at root_dir with a specified indentation.
    """
    if not os.path.exists(root_dir):
        print(f"Directory '{root_dir}' does not exist.")
        return

    print(indent + os.path.basename(root_dir) + os.path.sep)
    indent += "│   "

    items = os.listdir(root_dir)
    items.sort(key=lambda x: os.path.isfile(os.path.join(root_dir, x)), reverse=True)

    for index, item in enumerate(items):
        if index == len(items) - 1:
            new_indent = indent[:-1] + "└── "
        else:
            new_indent = indent[:-1] + "├── "

        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path):
            print(new_indent + item + os.path.sep)
            print_directory_tree(item_path, indent + "    ")
        else:
            print(new_indent + item)
