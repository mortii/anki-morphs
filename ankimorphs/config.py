from typing import Any, Optional, Union

from aqt import mw
from aqt.qt import QKeySequence  # pylint:disable=no-name-in-module


def get_config(
    key: str,
) -> Union[str, int, bool, list[dict[str, Union[str, bool, list[str], None]]], None]:
    config = get_configs()
    assert config
    item = config[key]
    assert isinstance(item, (str, bool, int, list))
    return item


def get_configs() -> Optional[dict[str, Any]]:
    assert mw
    return mw.addonManager.getConfig(__name__)


def get_default_config(key: str) -> Any:
    config = get_all_default_configs()
    assert config
    return config[key]


def get_all_default_configs() -> Optional[dict[str, Any]]:
    assert mw
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    return mw.addonManager.addonConfigDefaults(addon)


def update_configs(new_configs: dict[str, Union[str, int, bool, list[Any]]]) -> None:
    assert mw
    config = mw.addonManager.getConfig(__name__)
    assert config
    for key, value in new_configs.items():
        config[key] = value
    mw.addonManager.writeConfig(__name__, config)


def get_read_filters() -> list[dict[str, Optional[Union[str, bool, list[str]]]]]:
    config_filters = get_config("filters")
    assert isinstance(config_filters, list)
    read_filters = []
    for config_filter in config_filters:
        if config_filter["read"]:
            read_filters.append(config_filter)
    return read_filters


class AnkiMorphsConfig:
    def __init__(self) -> None:
        self.shortcut_browse_same_unknown_ripe: QKeySequence = _get_key_sequence_config(
            "shortcut_browse_same_unknown_ripe"
        )
        self.shortcut_browse_same_unknown_ripe_budding: QKeySequence = (
            _get_key_sequence_config("shortcut_browse_same_unknown_ripe_budding")
        )
        self.shortcut_set_known_and_skip: QKeySequence = _get_key_sequence_config(
            "shortcut_set_known_and_skip"
        )
        self.shortcut_learn_now: QKeySequence = _get_key_sequence_config(
            "shortcut_learn_now"
        )
        self.shortcut_view_morphemes: QKeySequence = _get_key_sequence_config(
            "shortcut_view_morphemes"
        )
        self.skip_stale_cards: bool = _get_bool_config("skip_stale_cards")
        self.skip_unknown_morph_seen_today_cards: bool = _get_bool_config(
            "skip_unknown_morph_seen_today_cards"
        )
        self.skip_show_num_of_skipped_cards: bool = _get_bool_config(
            "skip_show_num_of_skipped_cards"
        )
        self.recalc_ignore_suspended_leeches = _get_bool_config(
            "recalc_ignore_suspended_leeches"
        )
        self.recalc_always_prioritize_frequency_morphs: bool = _get_bool_config(
            "recalc_always_prioritize_frequency_morphs"
        )
        self.recalc_preferred_sentence_length: int = _get_int_config(
            "recalc_preferred_sentence_length"
        )
        self.recalc_unknown_morphs_count: int = _get_int_config(
            "recalc_unknown_morphs_count"
        )
        self.recalc_before_sync: bool = _get_bool_config("recalc_before_sync")
        self.recalc_prioritize_collection: bool = _get_bool_config(
            "recalc_prioritize_collection"
        )
        self.recalc_prioritize_textfile: bool = _get_bool_config(
            "recalc_prioritize_textfile"
        )
        self.parse_ignore_bracket_contents: bool = _get_bool_config(
            "parse_ignore_bracket_contents"
        )
        self.parse_ignore_round_bracket_contents: bool = _get_bool_config(
            "parse_ignore_round_bracket_contents"
        )
        self.parse_ignore_slim_round_bracket_contents: bool = _get_bool_config(
            "parse_ignore_slim_round_bracket_contents"
        )
        self.parse_ignore_proper_nouns: bool = _get_bool_config(
            "parse_ignore_proper_nouns"
        )
        self.parse_ignore_suspended_cards_content: bool = _get_bool_config(
            "parse_ignore_suspended_cards_content"
        )
        self.tag_ripe: str = _get_string_config("tag_ripe")
        self.tag_budding: str = _get_string_config("tag_budding")
        self.tag_stale: str = _get_string_config("tag_stale")

        # TODO add filters


def _get_key_sequence_config(key: str) -> QKeySequence:
    config_item = get_config(key)
    assert isinstance(config_item, str)
    return QKeySequence(config_item)


def _get_int_config(key: str) -> int:
    config_item = get_config(key)
    assert isinstance(config_item, int)
    return config_item


def _get_string_config(key: str) -> str:
    config_item = get_config(key)
    assert isinstance(config_item, str)
    return config_item


def _get_bool_config(key: str) -> bool:
    config_item = get_config(key)
    assert isinstance(config_item, bool)
    return config_item
