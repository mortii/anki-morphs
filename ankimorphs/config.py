from typing import Any, Optional, Union

from anki.notes import Note
from aqt import mw
from aqt.qt import QKeySequence  # pylint:disable=no-name-in-module


def get_config(key) -> Union[str, int, bool, list]:
    config = get_configs()
    return config[key]


def get_configs():
    return mw.addonManager.getConfig(__name__)


def get_default_config(key):
    config = get_all_default_configs()
    return config[key]


def get_all_default_configs():
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    return mw.addonManager.addonConfigDefaults(addon)


def update_configs(new_configs) -> None:
    config = mw.addonManager.getConfig(__name__)

    for key, value in new_configs.items():
        config[key] = value
    mw.addonManager.writeConfig(__name__, config)


def get_read_filters() -> list:
    config_filters = get_config("filters")
    read_filters = []
    for config_filter in config_filters:
        if config_filter["read"]:
            read_filters.append(config_filter)
    return read_filters


# Filters are the 'note filter' option in morphman gui preferences on which note types they want morphman to handle
# If a note is matched multiple times only the first filter in the list will be used
def get_filter(note: Note) -> Optional[dict]:
    note_type = note.note_type()["name"]
    return get_filter_by_type_and_tags(note_type, note.tags)


def get_filter_by_mid_and_tags(mid: Any, tags: list[str]) -> Optional[dict]:
    return get_filter_by_type_and_tags(mw.col.models.get(mid)["name"], tags)


def get_filter_by_type_and_tags(note_type: str, note_tags: list[str]) -> Optional[dict]:
    # TODO NEVER ALLOW NONE?
    for note_filter in get_config("filters"):
        if (
            note_type == note_filter["type"] or note_filter["type"] is None
        ):  # None means 'All note types' is selected
            note_tags = set(note_tags)
            note_filter_tags = set(note_filter["tags"])
            if note_filter_tags.issubset(
                note_tags
            ):  # required tags have to be subset of actual tags
                return note_filter
    return None  # card did not match (note type and tags) set in preferences GUI


def get_read_enabled_models():
    included_types = set()
    include_all = False
    for _filter in get_config("filters"):
        if _filter.get("read", True):
            if _filter["type"] is not None:
                included_types.add(_filter["type"])
            else:
                include_all = True
                break
    return included_types, include_all


def get_modify_enabled_models():
    included_types = set()
    include_all = False
    for _filter in get_config("filters"):
        if _filter.get("modify", True):
            if _filter["type"] is not None:
                included_types.add(_filter["type"])
            else:
                include_all = True
                break
    return included_types, include_all


class AnkiMorphsConfig:
    def __init__(self) -> None:
        self.tag_ripe = get_config("tag_ripe")
        self.tag_budding = get_config("tag_budding")
        self.shortcut_learn_now = QKeySequence(get_config("shortcut_learn_now"))
        self.shortcut_browse_same_unknown_ripe = QKeySequence(
            get_config("shortcut_browse_same_unknown_ripe")
        )
        self.shortcut_view_morphemes = QKeySequence(
            get_config("shortcut_view_morphemes")
        )
        self.shortcut_set_known_and_skip = QKeySequence(
            get_config("shortcut_set_known_and_skip")
        )
