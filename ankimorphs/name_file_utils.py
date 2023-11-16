import functools
import os

from aqt import mw


def add_name_to_file(selected_text: str) -> None:
    assert mw is not None

    selected_text.strip()
    names = selected_text.split()

    profile_path: str = mw.pm.profileFolder()
    path: str = os.path.join(profile_path, "names.txt")

    with open(path, mode="a", encoding="utf-8") as file:
        for name in names:
            file.write("\n" + name)

    # clear the cache so the new name(s) are included
    get_names_from_file.cache_clear()


@functools.cache
def get_names_from_file() -> set[str]:
    assert mw is not None

    profile_path: str = mw.pm.profileFolder()
    path: str = os.path.join(profile_path, "names.txt")

    # 'a+' creates the file if it does not exist (w+ overwrites the content)
    with open(path, mode="a+", encoding="utf-8") as names_file:
        # 'a'-mode moves the cursor to the end of the file automatically,
        # seek(0) moves the cursor to the beginning of the file.
        names_file.seek(0)

        # filter out empty lines
        lines_lower_case = filter(None, (line.strip().lower() for line in names_file))
        names = set(lines_lower_case)

    return names
