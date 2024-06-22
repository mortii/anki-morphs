################################################################
#                   ADDON SETTINGS/CONFIGS
################################################################
# Addons essentially only have one settings file that is shared
# across all anki profiles, that file is found here:
#    'Anki2/addons21/[addon]/meta.json'
#
# We extract the dictionary found in that file by using:
#   mw.addonManager.getConfig(__name__)
# where '__name__' is the module name of the addon
# (ankiweb switches the module name to a number, so it's necessary for this to be dynamic)
#
# We can update meta.json with this:
#   mw.addonManager.writeConfig(__name__, new_json_dict)

# We want to have individual profile settings, and we achieve this by storing
# a file ("ankimorphs_profile_settings.json") in the individual profile folders.
# When a profile is loaded by anki, that file is used to overwrite/update meta.json.
################################################################

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from anki.models import NotetypeId
from anki.notes import Note
from aqt import mw
from aqt.qt import (  # pylint:disable=no-name-in-module
    QKeySequence,
    QMessageBox,
    QPushButton,
    Qt,
)
from aqt.utils import tooltip

from . import ankimorphs_globals

# Unfortunately, 'TypeAlias' is introduced in python 3.10 so for now
# we can only create implicit type aliases. We also have to use the
# 'Union' notation even though we use '__future__ import annotations'.
FilterTypeAlias = dict[str, Union[str, bool, int, dict[str, str], None]]


class RawConfigFilterKeys:
    NOTE_TYPE = "note_type"
    TAGS = "tags"
    FIELD = "field"
    MORPHEMIZER_DESCRIPTION = "morphemizer_description"
    MORPH_PRIORITY = "morph_priority"  # todo rename this to "morph_priority_selection"?
    READ = "read"
    MODIFY = "modify"
    EXTRA_UNKNOWNS = "extra_unknowns"
    EXTRA_UNKNOWNS_COUNT = "extra_unknowns_count"
    EXTRA_HIGHLIGHTED = "extra_highlighted"
    EXTRA_SCORE = "extra_score"
    EXTRA_SCORE_TERMS = "extra_score_terms"


class RawConfigKeys:
    FILTERS = "filters"
    SHORTCUT_RECALC = "shortcut_recalc"
    SHORTCUT_SETTINGS = "shortcut_settings"
    SHORTCUT_BROWSE_READY_SAME_UNKNOWN = "shortcut_browse_ready_same_unknown"
    SHORTCUT_BROWSE_ALL_SAME_UNKNOWN = "shortcut_browse_all_same_unknown"
    SHORTCUT_BROWSE_READY_SAME_UNKNOWN_LEMMA = (
        "shortcut_browse_ready_same_unknown_lemma"
    )
    SHORTCUT_SET_KNOWN_AND_SKIP = "shortcut_set_known_and_skip"
    SHORTCUT_LEARN_NOW = "shortcut_learn_now"
    SHORTCUT_VIEW_MORPHEMES = "shortcut_view_morphemes"
    SHORTCUT_GENERATORS = "shortcut_generators"
    SHORTCUT_KNOWN_MORPHS_EXPORTER = "shortcut_known_morphs_exporter"
    SKIP_ONLY_KNOWN_MORPHS_CARDS = "skip_only_known_morphs_cards"
    SKIP_UNKNOWN_MORPH_SEEN_TODAY_CARDS = "skip_unknown_morph_seen_today_cards"
    SKIP_SHOW_NUM_OF_SKIPPED_CARDS = "skip_show_num_of_skipped_cards"
    PREPROCESS_IGNORE_BRACKET_CONTENTS = "preprocess_ignore_bracket_contents"
    PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS = (
        "preprocess_ignore_round_bracket_contents"
    )
    PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS = (
        "preprocess_ignore_slim_round_bracket_contents"
    )
    PREPROCESS_IGNORE_NAMES_MORPHEMIZER = "preprocess_ignore_names_morphemizer"
    PREPROCESS_IGNORE_NAMES_TEXTFILE = "preprocess_ignore_names_textfile"
    PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT = (
        "preprocess_ignore_suspended_cards_content"
    )
    RECALC_INTERVAL_FOR_KNOWN = "recalc_interval_for_known"
    RECALC_ON_SYNC = "recalc_on_sync"
    RECALC_SUSPEND_KNOWN_NEW_CARDS = "recalc_suspend_known_new_cards"
    RECALC_READ_KNOWN_MORPHS_FOLDER = "recalc_read_known_morphs_folder"
    RECALC_TOOLBAR_STATS_USE_SEEN = "recalc_toolbar_stats_use_seen"
    RECALC_TOOLBAR_STATS_USE_KNOWN = "recalc_toolbar_stats_use_known"
    RECALC_UNKNOWNS_FIELD_SHOWS_INFLECTIONS = "recalc_unknowns_field_shows_inflections"
    RECALC_UNKNOWNS_FIELD_SHOWS_LEMMAS = "recalc_unknowns_field_shows_lemmas"
    RECALC_OFFSET_NEW_CARDS = "recalc_offset_new_cards"
    RECALC_DUE_OFFSET = "recalc_due_offset"
    RECALC_NUMBER_OF_MORPHS_TO_OFFSET = "recalc_number_of_morphs_to_offset"
    RECALC_MOVE_KNOWN_NEW_CARDS_TO_THE_END = "recalc_move_known_new_cards_to_the_end"
    TAG_READY = "tag_ready"
    TAG_NOT_READY = "tag_not_ready"
    TAG_KNOWN_AUTOMATICALLY = "tag_known_automatically"
    TAG_KNOWN_MANUALLY = "tag_known_manually"
    TAG_LEARN_CARD_NOW = "tag_learn_card_now"
    EVALUATE_MORPH_LEMMA = "evaluate_morph_lemma"
    EVALUATE_MORPH_INFLECTION = "evaluate_morph_inflection"
    ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS = "algorithm_total_priority_unknown_morphs"
    ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS = "algorithm_total_priority_all_morphs"
    ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS = "algorithm_average_priority_all_morphs"
    ALGORITHM_ALL_MORPHS_TARGET_DISTANCE = "algorithm_all_morphs_target_distance"
    ALGORITHM_LEARNING_MORPHS_TARGET_DISTANCE = (
        "algorithm_learning_morphs_target_distance"
    )
    ALGORITHM_UPPER_TARGET_ALL_MORPHS = "algorithm_upper_target_all_morphs"
    ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_A = (
        "algorithm_upper_target_all_morphs_coefficient_a"
    )
    ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_B = (
        "algorithm_upper_target_all_morphs_coefficient_b"
    )
    ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_C = (
        "algorithm_upper_target_all_morphs_coefficient_c"
    )
    ALGORITHM_LOWER_TARGET_ALL_MORPHS = "algorithm_lower_target_all_morphs"
    ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_A = (
        "algorithm_lower_target_all_morphs_coefficient_a"
    )
    ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_B = (
        "algorithm_lower_target_all_morphs_coefficient_b"
    )
    ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_C = (
        "algorithm_lower_target_all_morphs_coefficient_c"
    )
    ALGORITHM_UPPER_TARGET_LEARNING_MORPHS = "algorithm_upper_target_learning_morphs"
    ALGORITHM_LOWER_TARGET_LEARNING_MORPHS = "algorithm_lower_target_learning_morphs"
    ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_A = (
        "algorithm_upper_target_learning_morphs_coefficient_a"
    )
    ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_B = (
        "algorithm_upper_target_learning_morphs_coefficient_b"
    )
    ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_C = (
        "algorithm_upper_target_learning_morphs_coefficient_c"
    )
    ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_A = (
        "algorithm_lower_target_learning_morphs_coefficient_a"
    )
    ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_B = (
        "algorithm_lower_target_learning_morphs_coefficient_b"
    )
    ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_C = (
        "algorithm_lower_target_learning_morphs_coefficient_c"
    )
    HIDE_RECALC_TOOLBAR = "hide_recalc_toolbar"
    HIDE_LEMMA_TOOLBAR = "hide_lemma_toolbar"
    HIDE_INFLECTION_TOOLBAR = "hide_inflection_toolbar"


class AnkiMorphsConfigFilter:  # pylint:disable=too-many-instance-attributes
    def __init__(self, _filter: FilterTypeAlias):
        try:
            self.has_error: bool = False
            self.note_type: str = _get_filter_str(
                _filter, RawConfigFilterKeys.NOTE_TYPE
            )
            self.tags: dict[str, str] = _get_filter_str_from_json(
                _filter, RawConfigFilterKeys.TAGS
            )
            self.field: str = _get_filter_str(_filter, RawConfigFilterKeys.FIELD)
            self.morphemizer_description: str = _get_filter_str(
                _filter, RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION
            )
            self.morph_priority_selection: str = _get_filter_str(
                _filter, RawConfigFilterKeys.MORPH_PRIORITY
            )
            self.read: bool = _get_filter_bool(_filter, RawConfigFilterKeys.READ)
            self.modify: bool = _get_filter_bool(_filter, RawConfigFilterKeys.MODIFY)
            self.extra_unknowns: bool = _get_filter_bool(
                _filter, RawConfigFilterKeys.EXTRA_UNKNOWNS
            )
            self.extra_unknowns_count: bool = _get_filter_bool(
                _filter, RawConfigFilterKeys.EXTRA_UNKNOWNS_COUNT
            )
            self.extra_highlighted: bool = _get_filter_bool(
                _filter, RawConfigFilterKeys.EXTRA_HIGHLIGHTED
            )
            self.extra_score: bool = _get_filter_bool(
                _filter, RawConfigFilterKeys.EXTRA_SCORE
            )
            self.extra_score_terms: bool = _get_filter_bool(
                _filter, RawConfigFilterKeys.EXTRA_SCORE_TERMS
            )

        # except (KeyError, AssertionError):
        except AssertionError:
            self.has_error = True
            if not ankimorphs_globals.ankimorphs_config_broken:
                show_critical_config_error()
                ankimorphs_globals.ankimorphs_config_broken = True


class AnkiMorphsConfig:  # pylint:disable=too-many-instance-attributes, too-many-statements
    def __init__(self, is_default: bool = False) -> None:
        try:
            self.shortcut_recalc: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_RECALC, is_default
            )
            self.shortcut_settings: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_SETTINGS, is_default
            )
            self.shortcut_browse_ready_same_unknown: QKeySequence = (
                _get_key_sequence_config(
                    RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN, is_default
                )
            )
            self.shortcut_browse_all_same_unknown: QKeySequence = (
                _get_key_sequence_config(
                    RawConfigKeys.SHORTCUT_BROWSE_ALL_SAME_UNKNOWN, is_default
                )
            )
            self.shortcut_browse_ready_same_unknown_lemma: QKeySequence = (
                _get_key_sequence_config(
                    RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN_LEMMA, is_default
                )
            )
            self.shortcut_set_known_and_skip: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_SET_KNOWN_AND_SKIP, is_default
            )
            self.shortcut_learn_now: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_LEARN_NOW, is_default
            )
            self.shortcut_view_morphemes: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_VIEW_MORPHEMES, is_default
            )
            self.shortcut_generators: QKeySequence = _get_key_sequence_config(
                RawConfigKeys.SHORTCUT_GENERATORS, is_default
            )
            self.shortcut_known_morphs_exporter: QKeySequence = (
                _get_key_sequence_config(
                    RawConfigKeys.SHORTCUT_KNOWN_MORPHS_EXPORTER, is_default
                )
            )
            self.skip_only_known_morphs_cards: bool = _get_bool_config(
                RawConfigKeys.SKIP_ONLY_KNOWN_MORPHS_CARDS, is_default
            )
            self.skip_unknown_morph_seen_today_cards: bool = _get_bool_config(
                RawConfigKeys.SKIP_UNKNOWN_MORPH_SEEN_TODAY_CARDS, is_default
            )
            self.skip_show_num_of_skipped_cards: bool = _get_bool_config(
                RawConfigKeys.SKIP_SHOW_NUM_OF_SKIPPED_CARDS, is_default
            )
            self.preprocess_ignore_bracket_contents: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS, is_default
            )
            self.preprocess_ignore_round_bracket_contents: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS, is_default
            )
            self.preprocess_ignore_slim_round_bracket_contents: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS, is_default
            )
            self.preprocess_ignore_names_morphemizer: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_NAMES_MORPHEMIZER, is_default
            )
            self.preprocess_ignore_names_textfile: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_NAMES_TEXTFILE, is_default
            )
            self.preprocess_ignore_suspended_cards_content: bool = _get_bool_config(
                RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT, is_default
            )
            self.recalc_interval_for_known: int = _get_int_config(
                RawConfigKeys.RECALC_INTERVAL_FOR_KNOWN, is_default
            )
            self.recalc_on_sync: bool = _get_bool_config(
                RawConfigKeys.RECALC_ON_SYNC, is_default
            )
            self.recalc_suspend_known_new_cards: bool = _get_bool_config(
                RawConfigKeys.RECALC_SUSPEND_KNOWN_NEW_CARDS, is_default
            )
            self.recalc_read_known_morphs_folder: bool = _get_bool_config(
                RawConfigKeys.RECALC_READ_KNOWN_MORPHS_FOLDER, is_default
            )
            self.recalc_toolbar_stats_use_seen: bool = _get_bool_config(
                RawConfigKeys.RECALC_TOOLBAR_STATS_USE_SEEN, is_default
            )
            self.recalc_toolbar_stats_use_known: bool = _get_bool_config(
                RawConfigKeys.RECALC_TOOLBAR_STATS_USE_KNOWN, is_default
            )
            self.recalc_unknowns_field_shows_inflections: bool = _get_bool_config(
                RawConfigKeys.RECALC_UNKNOWNS_FIELD_SHOWS_INFLECTIONS, is_default
            )
            self.recalc_unknowns_field_shows_lemmas: bool = _get_bool_config(
                RawConfigKeys.RECALC_UNKNOWNS_FIELD_SHOWS_LEMMAS, is_default
            )
            self.recalc_offset_new_cards: bool = _get_bool_config(
                RawConfigKeys.RECALC_OFFSET_NEW_CARDS, is_default
            )
            self.recalc_due_offset: int = _get_int_config(
                RawConfigKeys.RECALC_DUE_OFFSET, is_default
            )
            self.recalc_number_of_morphs_to_offset: int = _get_int_config(
                RawConfigKeys.RECALC_NUMBER_OF_MORPHS_TO_OFFSET, is_default
            )
            self.recalc_move_known_new_cards_to_the_end: bool = _get_bool_config(
                RawConfigKeys.RECALC_MOVE_KNOWN_NEW_CARDS_TO_THE_END, is_default
            )
            self.tag_ready: str = _get_string_config(
                RawConfigKeys.TAG_READY, is_default
            )
            self.tag_not_ready: str = _get_string_config(
                RawConfigKeys.TAG_NOT_READY, is_default
            )
            self.tag_known_automatically: str = _get_string_config(
                RawConfigKeys.TAG_KNOWN_AUTOMATICALLY, is_default
            )
            self.tag_known_manually: str = _get_string_config(
                RawConfigKeys.TAG_KNOWN_MANUALLY, is_default
            )
            self.tag_learn_card_now: str = _get_string_config(
                RawConfigKeys.TAG_LEARN_CARD_NOW, is_default
            )
            self.evaluate_morph_lemma: bool = _get_bool_config(
                RawConfigKeys.EVALUATE_MORPH_LEMMA, is_default
            )
            self.evaluate_morph_inflection: bool = _get_bool_config(
                RawConfigKeys.EVALUATE_MORPH_INFLECTION, is_default
            )
            self.algorithm_total_priority_unknown_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS, is_default
            )
            self.algorithm_total_priority_all_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS, is_default
            )
            self.algorithm_average_priority_all_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS, is_default
            )
            self.algorithm_all_morphs_target_distance: int = _get_int_config(
                RawConfigKeys.ALGORITHM_ALL_MORPHS_TARGET_DISTANCE, is_default
            )
            self.algorithm_learning_morphs_target_distance: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LEARNING_MORPHS_TARGET_DISTANCE, is_default
            )
            self.algorithm_upper_target_all_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS, is_default
            )
            self.algorithm_upper_target_all_morphs_coefficient_a: int = _get_int_config(
                RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_A,
                is_default,
            )
            self.algorithm_upper_target_all_morphs_coefficient_b: int = _get_int_config(
                RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_B,
                is_default,
            )
            self.algorithm_upper_target_all_morphs_coefficient_c: int = _get_int_config(
                RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_C,
                is_default,
            )
            self.algorithm_lower_target_all_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS, is_default
            )
            self.algorithm_lower_target_all_morphs_coefficient_a: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_A,
                is_default,
            )
            self.algorithm_lower_target_all_morphs_coefficient_b: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_B,
                is_default,
            )
            self.algorithm_lower_target_all_morphs_coefficient_c: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_C,
                is_default,
            )
            self.algorithm_upper_target_learning_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS, is_default
            )
            self.algorithm_lower_target_learning_morphs: int = _get_int_config(
                RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS, is_default
            )
            self.algorithm_upper_target_learning_morphs_coefficient_a: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_A,
                    is_default,
                )
            )
            self.algorithm_upper_target_learning_morphs_coefficient_b: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_B,
                    is_default,
                )
            )
            self.algorithm_upper_target_learning_morphs_coefficient_c: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_C,
                    is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_a: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_A,
                    is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_b: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_B,
                    is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_c: int = (
                _get_int_config(
                    RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_C,
                    is_default,
                )
            )
            self.hide_recalc_toolbar: bool = _get_bool_config(
                RawConfigKeys.HIDE_RECALC_TOOLBAR, is_default
            )
            self.hide_lemma_toolbar: bool = _get_bool_config(
                RawConfigKeys.HIDE_LEMMA_TOOLBAR, is_default
            )
            self.hide_inflection_toolbar: bool = _get_bool_config(
                RawConfigKeys.HIDE_INFLECTION_TOOLBAR, is_default
            )

            self.filters: list[AnkiMorphsConfigFilter] = _get_filters_config(is_default)

        # except (KeyError, AssertionError):
        except AssertionError:
            if not ankimorphs_globals.ankimorphs_config_broken:
                show_critical_config_error()
                ankimorphs_globals.ankimorphs_config_broken = True
        finally:
            # todo: add this to filter too
            if ankimorphs_globals.ankimorphs_new_config_found:
                show_warning_new_config_items()

    def update(self) -> None:
        # The same AnkiMorphsSettings object is shared many
        # places (SettingsTabs, etc.), and to avoid de-synchronization
        # it is better to update the object rather than creating
        # new objects/updating the references.
        new_config = AnkiMorphsConfig()
        self.__dict__.update(new_config.__dict__)


def _get_config(
    key: str,
) -> str | int | bool | list[FilterTypeAlias] | None:
    config = get_configs()
    assert config is not None
    try:
        item = config[key]
    except KeyError:
        ankimorphs_globals.ankimorphs_new_config_found = True
        item = get_default_config(key)
    assert isinstance(item, (str, bool, int, list))
    return item


def get_configs() -> dict[str, Any] | None:
    assert mw is not None
    return mw.addonManager.getConfig(__name__)


def get_default_config(key: str) -> Any:
    config = get_all_default_configs()
    assert config is not None
    return config[key]


def get_all_default_configs() -> dict[str, Any] | None:
    assert mw is not None
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    return mw.addonManager.addonConfigDefaults(addon)


def update_configs(new_configs: dict[str, str | int | bool | object]) -> None:
    assert mw is not None
    config = mw.addonManager.getConfig(__name__)
    assert config is not None
    for key, value in new_configs.items():
        config[key] = value

    mw.addonManager.writeConfig(__name__, config)

    # also write to the profile settings file
    profile_settings_path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.PROFILE_SETTINGS_FILE_NAME
    )
    with open(profile_settings_path, mode="w", encoding="utf-8") as file:
        json.dump(config, file)


def reset_all_configs() -> None:
    default_configs = get_all_default_configs()
    assert default_configs is not None
    update_configs(default_configs)


def get_read_enabled_filters() -> list[AnkiMorphsConfigFilter]:
    config_filters = _get_filters_config()
    assert isinstance(config_filters, list)
    read_filters = []
    for config_filter in config_filters:
        if config_filter.read:
            read_filters.append(config_filter)
    return read_filters


def get_modify_enabled_filters() -> list[AnkiMorphsConfigFilter]:
    config_filters = _get_filters_config()
    assert isinstance(config_filters, list)
    modify_filters = []
    for config_filter in config_filters:
        if config_filter.modify:
            modify_filters.append(config_filter)
    return modify_filters


def get_matching_modify_filter(note: Note) -> AnkiMorphsConfigFilter | None:
    assert mw is not None
    modify_filters: list[AnkiMorphsConfigFilter] = get_modify_enabled_filters()
    for am_filter in modify_filters:
        note_type_id: NotetypeId | None = mw.col.models.id_for_name(am_filter.note_type)
        if note_type_id == note.mid:
            return am_filter
    return None


def get_matching_read_filter(note: Note) -> AnkiMorphsConfigFilter | None:
    assert mw is not None
    read_filters: list[AnkiMorphsConfigFilter] = get_read_enabled_filters()
    for am_filter in read_filters:
        note_type_id: NotetypeId | None = mw.col.models.id_for_name(am_filter.note_type)
        if note_type_id == note.mid:
            return am_filter
    return None


def _get_filters_config(is_default: bool = False) -> list[AnkiMorphsConfigFilter]:
    if is_default:
        filters_config = get_default_config("filters")
    else:
        filters_config = _get_config("filters")
    assert isinstance(filters_config, list)

    filters = []
    for _filter in filters_config:
        am_filter = AnkiMorphsConfigFilter(_filter)
        if not am_filter.has_error:
            filters.append(am_filter)
    return filters


def _get_key_sequence_config(key: str, is_default: bool = False) -> QKeySequence:
    if is_default:
        config_item = get_default_config(key)
    else:
        config_item = _get_config(key)
    assert isinstance(config_item, str)
    return QKeySequence(config_item)


def _get_int_config(key: str, is_default: bool = False) -> int:
    if is_default:
        config_item = get_default_config(key)
    else:
        config_item = _get_config(key)
    assert isinstance(config_item, int)
    return config_item


def _get_string_config(key: str, is_default: bool = False) -> str:
    if is_default:
        config_item = get_default_config(key)
    else:
        config_item = _get_config(key)
    assert isinstance(config_item, str)
    return config_item


def _get_bool_config(key: str, is_default: bool = False) -> bool:
    if is_default:
        config_item = get_default_config(key)
    else:
        config_item = _get_config(key)
    assert isinstance(config_item, bool)
    return config_item


def _get_filter_str(_filter: FilterTypeAlias, key: str) -> str:
    filter_item = _filter[key]
    assert isinstance(filter_item, str)
    return filter_item


def _get_filter_bool(_filter: FilterTypeAlias, key: str) -> bool:
    try:
        filter_item = _filter[key]
    except KeyError:
        # Silently ignoring this and just adding the non-activated default value
        # is a much better user experience than crashing/getting an error message.
        # The default filters config is a list with one entry which contains default values.
        filter_item = get_default_config("filters")[0][key]
    assert isinstance(filter_item, bool)
    return filter_item


def _get_filter_str_from_json(_filter: FilterTypeAlias, key: str) -> dict[str, str]:
    filter_item_dict = _filter[key]
    assert isinstance(filter_item_dict, dict)
    return filter_item_dict


def show_critical_config_error() -> None:
    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle("AnkiMorphs Error")
    critical_box.setIcon(QMessageBox.Icon.Critical)
    ok_button: QPushButton = QPushButton("Restore All Defaults")
    critical_box.addButton(ok_button, QMessageBox.ButtonRole.YesRole)
    body: str = (
        "**The default AnkiMorphs configs have been changed!**"
        "<br/><br/>"
        "Backwards compatibility has been broken, "
        "read the <a href='https://github.com/mortii/anki-morphs/releases'>changelog</a> for more info."
        "<br/><br/>"
        "Please do the following:\n"
        "1. Click the 'Restore All Defaults' button below\n"
        "2. Redo your AnkiMorphs settings\n\n"
    )
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    critical_box.setText(body)
    critical_box.exec()

    if critical_box.clickedButton() == ok_button:
        reset_all_configs()
        tooltip("Please restart Anki", period=5000, parent=mw)


def show_warning_new_config_items() -> None:
    # todo: update this
    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle("AnkiMorphs Error")
    critical_box.setIcon(QMessageBox.Icon.Critical)
    # ok_button: QPushButton = QPushButton("Restore All Defaults")
    # critical_box.addButton(ok_button, QMessageBox.ButtonRole.YesRole)
    body: str = (
        "**NEW default AnkiMorphs configs FOUND!**"
        "<br/><br/>"
        "Backwards compatibility has been broken, "
        "read the <a href='https://github.com/mortii/anki-morphs/releases'>changelog</a> for more info."
        "<br/><br/>"
        "Please do the following:\n"
        "1. Click the 'Restore All Defaults' button below\n"
        "2. Redo your AnkiMorphs settings\n\n"
    )
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    critical_box.setText(body)
    critical_box.exec()

    # if critical_box.clickedButton() == ok_button:
    #     reset_all_configs()
    #     tooltip("Please restart Anki", period=5000, parent=mw)
