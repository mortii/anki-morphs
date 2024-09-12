###################################################################################
#                               ADDON SETTINGS/CONFIGS
###################################################################################

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
#
# We want to have individual profile settings, and we achieve this by storing
# a file ("ankimorphs_profile_settings.json") in the individual profile folders.
# When a profile is loaded by anki, that file is used to overwrite/update meta.json.
###################################################################################

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
    MORPH_PRIORITY_SELECTION = "morph_priority_selection"
    READ = "read"
    MODIFY = "modify"
    EXTRA_ALL_MORPHS = "extra_all_morphs"
    EXTRA_ALL_MORPHS_COUNT = "extra_all_morphs_count"
    EXTRA_UNKNOWN_MORPHS = "extra_unknown_morphs"
    EXTRA_UNKNOWN_MORPHS_COUNT = "extra_unknown_morphs_count"
    EXTRA_HIGHLIGHTED = "extra_highlighted"
    EXTRA_SCORE = "extra_score"
    EXTRA_SCORE_TERMS = "extra_score_terms"
    EXTRA_STUDY_MORPHS = "extra_study_morphs"


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
    SHORTCUT_PROGRESSION = "shortcut_progression"
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
    PREPROCESS_IGNORE_CUSTOM_CHARACTERS = "preprocess_ignore_custom_characters"
    PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE = "preprocess_custom_characters_to_ignore"
    INTERVAL_FOR_KNOWN_MORPHS = "interval_for_known_morphs"
    RECALC_ON_SYNC = "recalc_on_sync"
    RECALC_SUSPEND_KNOWN_NEW_CARDS = "recalc_suspend_known_new_cards"
    READ_KNOWN_MORPHS_FOLDER = "read_known_morphs_folder"
    TOOLBAR_STATS_USE_KNOWN = "toolbar_stats_use_known"
    TOOLBAR_STATS_USE_SEEN = "toolbar_stats_use_seen"
    EXTRA_FIELDS_DISPLAY_INFLECTIONS = "extra_fields_display_inflections"
    EXTRA_FIELDS_DISPLAY_LEMMAS = "extra_fields_display_lemmas"
    RECALC_OFFSET_NEW_CARDS = "recalc_offset_new_cards"
    RECALC_DUE_OFFSET = "recalc_due_offset"
    RECALC_NUMBER_OF_MORPHS_TO_OFFSET = "recalc_number_of_morphs_to_offset"
    RECALC_MOVE_KNOWN_NEW_CARDS_TO_THE_END = "recalc_move_known_new_cards_to_the_end"
    TAG_FRESH = "tag_fresh"
    TAG_READY = "tag_ready"
    TAG_NOT_READY = "tag_not_ready"
    TAG_KNOWN_AUTOMATICALLY = "tag_known_automatically"
    TAG_KNOWN_MANUALLY = "tag_known_manually"
    TAG_LEARN_CARD_NOW = "tag_learn_card_now"
    EVALUATE_MORPH_LEMMA = "evaluate_morph_lemma"
    EVALUATE_MORPH_INFLECTION = "evaluate_morph_inflection"
    ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT = (
        "algorithm_total_priority_unknown_morphs_weight"
    )
    ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS_WEIGHT = (
        "algorithm_total_priority_all_morphs_weight"
    )
    ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS_WEIGHT = (
        "algorithm_average_priority_all_morphs_weight"
    )
    ALGORITHM_TOTAL_PRIORITY_LEARNING_MORPHS_WEIGHT = (
        "algorithm_total_priority_learning_morphs_weight"
    )
    ALGORITHM_AVERAGE_PRIORITY_LEARNING_MORPHS_WEIGHT = (
        "algorithm_average_priority_learning_morphs_weight"
    )
    ALGORITHM_ALL_MORPHS_TARGET_DIFFERENCE_WEIGHT = (
        "algorithm_all_morphs_target_difference_weight"
    )
    ALGORITHM_LEARNING_MORPHS_TARGET_DIFFERENCE_WEIGHT = (
        "algorithm_learning_morphs_target_difference_weight"
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
            self._filter = _filter
            self._default_config_dict = get_all_defaults_config_dict()
            self.has_error: bool = False

            self.note_type: str = self._get_filter_item(
                key=RawConfigFilterKeys.NOTE_TYPE, expected_type=str
            )
            self.tags: dict[str, str] = self._get_filter_item(
                key=RawConfigFilterKeys.TAGS, expected_type=dict
            )
            self.field: str = self._get_filter_item(
                key=RawConfigFilterKeys.FIELD, expected_type=str
            )
            self.morphemizer_description: str = self._get_filter_item(
                key=RawConfigFilterKeys.MORPHEMIZER_DESCRIPTION, expected_type=str
            )
            self.morph_priority_selection: str = self._get_filter_item(
                key=RawConfigFilterKeys.MORPH_PRIORITY_SELECTION, expected_type=str
            )
            self.read: bool = self._get_filter_item(
                key=RawConfigFilterKeys.READ, expected_type=bool
            )
            self.modify: bool = self._get_filter_item(
                key=RawConfigFilterKeys.MODIFY, expected_type=bool
            )
            self.extra_all_morphs: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_ALL_MORPHS, expected_type=bool
            )
            self.extra_all_morphs_count: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_ALL_MORPHS_COUNT, expected_type=bool
            )
            self.extra_unknown_morphs: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_UNKNOWN_MORPHS, expected_type=bool
            )
            self.extra_unknown_morphs_count: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_UNKNOWN_MORPHS_COUNT, expected_type=bool
            )
            self.extra_highlighted: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_HIGHLIGHTED, expected_type=bool
            )
            self.extra_score: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_SCORE, expected_type=bool
            )
            self.extra_score_terms: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_SCORE_TERMS, expected_type=bool
            )
            self.extra_study_morphs: bool = self._get_filter_item(
                key=RawConfigFilterKeys.EXTRA_STUDY_MORPHS, expected_type=bool
            )

        except AssertionError:
            self.has_error = True
            if not ankimorphs_globals.config_broken:
                show_critical_config_error()
                ankimorphs_globals.config_broken = True

    def _get_filter_item(self, key: str, expected_type: type) -> Any:
        try:
            filter_item = self._filter[key]
        except KeyError:
            filter_item = self._default_config_dict[RawConfigKeys.FILTERS][0][key]
            ankimorphs_globals.new_config_found = True
        assert isinstance(filter_item, expected_type)
        return filter_item


class AnkiMorphsConfig:  # pylint:disable=too-many-instance-attributes, too-many-statements
    def __init__(self, is_default: bool = False) -> None:
        try:
            self._config_dict = get_config_dict()
            self._default_config_dict = get_all_defaults_config_dict()

            self.shortcut_recalc: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_RECALC,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_settings: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_SETTINGS,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_browse_ready_same_unknown: QKeySequence = (
                self._get_key_sequence_config(
                    key=RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN,
                    expected_type=str,
                    use_default=is_default,
                )
            )
            self.shortcut_browse_all_same_unknown: QKeySequence = (
                self._get_key_sequence_config(
                    key=RawConfigKeys.SHORTCUT_BROWSE_ALL_SAME_UNKNOWN,
                    expected_type=str,
                    use_default=is_default,
                )
            )
            self.shortcut_browse_ready_same_unknown_lemma: QKeySequence = (
                self._get_key_sequence_config(
                    key=RawConfigKeys.SHORTCUT_BROWSE_READY_SAME_UNKNOWN_LEMMA,
                    expected_type=str,
                    use_default=is_default,
                )
            )
            self.shortcut_set_known_and_skip: QKeySequence = (
                self._get_key_sequence_config(
                    key=RawConfigKeys.SHORTCUT_SET_KNOWN_AND_SKIP,
                    expected_type=str,
                    use_default=is_default,
                )
            )
            self.shortcut_learn_now: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_LEARN_NOW,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_view_morphemes: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_VIEW_MORPHEMES,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_generators: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_GENERATORS,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_progression: QKeySequence = self._get_key_sequence_config(
                key=RawConfigKeys.SHORTCUT_PROGRESSION,
                expected_type=str,
                use_default=is_default,
            )
            self.shortcut_known_morphs_exporter: QKeySequence = (
                self._get_key_sequence_config(
                    key=RawConfigKeys.SHORTCUT_KNOWN_MORPHS_EXPORTER,
                    expected_type=str,
                    use_default=is_default,
                )
            )

            self.skip_only_known_morphs_cards: bool = self._get_config_item(
                key=RawConfigKeys.SKIP_ONLY_KNOWN_MORPHS_CARDS,
                expected_type=bool,
                use_default=is_default,
            )
            self.skip_unknown_morph_seen_today_cards: bool = self._get_config_item(
                key=RawConfigKeys.SKIP_UNKNOWN_MORPH_SEEN_TODAY_CARDS,
                expected_type=bool,
                use_default=is_default,
            )
            self.skip_show_num_of_skipped_cards: bool = self._get_config_item(
                key=RawConfigKeys.SKIP_SHOW_NUM_OF_SKIPPED_CARDS,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_ignore_bracket_contents: bool = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_ignore_round_bracket_contents: bool = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_ignore_slim_round_bracket_contents: bool = (
                self._get_config_item(
                    key=RawConfigKeys.PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS,
                    expected_type=bool,
                    use_default=is_default,
                )
            )
            self.preprocess_ignore_names_morphemizer: bool = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_IGNORE_NAMES_MORPHEMIZER,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_ignore_names_textfile: bool = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_IGNORE_NAMES_TEXTFILE,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_ignore_suspended_cards_content: bool = (
                self._get_config_item(
                    key=RawConfigKeys.PREPROCESS_IGNORE_SUSPENDED_CARDS_CONTENT,
                    expected_type=bool,
                    use_default=is_default,
                )
            )
            self.preprocess_ignore_custom_characters: bool = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS,
                expected_type=bool,
                use_default=is_default,
            )
            self.preprocess_custom_characters_to_ignore: str = self._get_config_item(
                key=RawConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE,
                expected_type=str,
                use_default=is_default,
            )
            self.interval_for_known_morphs: int = self._get_config_item(
                key=RawConfigKeys.INTERVAL_FOR_KNOWN_MORPHS,
                expected_type=int,
                use_default=is_default,
            )
            self.recalc_on_sync: bool = self._get_config_item(
                key=RawConfigKeys.RECALC_ON_SYNC,
                expected_type=bool,
                use_default=is_default,
            )
            self.recalc_suspend_known_new_cards: bool = self._get_config_item(
                key=RawConfigKeys.RECALC_SUSPEND_KNOWN_NEW_CARDS,
                expected_type=bool,
                use_default=is_default,
            )
            self.read_known_morphs_folder: bool = self._get_config_item(
                key=RawConfigKeys.READ_KNOWN_MORPHS_FOLDER,
                expected_type=bool,
                use_default=is_default,
            )
            self.toolbar_stats_use_known: bool = self._get_config_item(
                key=RawConfigKeys.TOOLBAR_STATS_USE_KNOWN,
                expected_type=bool,
                use_default=is_default,
            )
            self.toolbar_stats_use_seen: bool = self._get_config_item(
                key=RawConfigKeys.TOOLBAR_STATS_USE_SEEN,
                expected_type=bool,
                use_default=is_default,
            )
            self.extra_fields_display_inflections: bool = self._get_config_item(
                key=RawConfigKeys.EXTRA_FIELDS_DISPLAY_INFLECTIONS,
                expected_type=bool,
                use_default=is_default,
            )
            self.extra_fields_display_lemmas: bool = self._get_config_item(
                key=RawConfigKeys.EXTRA_FIELDS_DISPLAY_LEMMAS,
                expected_type=bool,
                use_default=is_default,
            )
            self.recalc_offset_new_cards: bool = self._get_config_item(
                key=RawConfigKeys.RECALC_OFFSET_NEW_CARDS,
                expected_type=bool,
                use_default=is_default,
            )
            self.recalc_due_offset: int = self._get_config_item(
                key=RawConfigKeys.RECALC_DUE_OFFSET,
                expected_type=int,
                use_default=is_default,
            )
            self.recalc_number_of_morphs_to_offset: int = self._get_config_item(
                key=RawConfigKeys.RECALC_NUMBER_OF_MORPHS_TO_OFFSET,
                expected_type=int,
                use_default=is_default,
            )
            self.recalc_move_known_new_cards_to_the_end: bool = self._get_config_item(
                key=RawConfigKeys.RECALC_MOVE_KNOWN_NEW_CARDS_TO_THE_END,
                expected_type=bool,
                use_default=is_default,
            )
            self.tag_fresh: str = self._get_config_item(
                key=RawConfigKeys.TAG_FRESH, expected_type=str, use_default=is_default
            )
            self.tag_ready: str = self._get_config_item(
                key=RawConfigKeys.TAG_READY, expected_type=str, use_default=is_default
            )
            self.tag_not_ready: str = self._get_config_item(
                key=RawConfigKeys.TAG_NOT_READY,
                expected_type=str,
                use_default=is_default,
            )
            self.tag_known_automatically: str = self._get_config_item(
                key=RawConfigKeys.TAG_KNOWN_AUTOMATICALLY,
                expected_type=str,
                use_default=is_default,
            )
            self.tag_known_manually: str = self._get_config_item(
                key=RawConfigKeys.TAG_KNOWN_MANUALLY,
                expected_type=str,
                use_default=is_default,
            )
            self.tag_learn_card_now: str = self._get_config_item(
                key=RawConfigKeys.TAG_LEARN_CARD_NOW,
                expected_type=str,
                use_default=is_default,
            )
            self.evaluate_morph_lemma: bool = self._get_config_item(
                key=RawConfigKeys.EVALUATE_MORPH_LEMMA,
                expected_type=bool,
                use_default=is_default,
            )
            self.evaluate_morph_inflection: bool = self._get_config_item(
                key=RawConfigKeys.EVALUATE_MORPH_INFLECTION,
                expected_type=bool,
                use_default=is_default,
            )
            self.algorithm_total_priority_unknown_morphs_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_UNKNOWN_MORPHS_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_total_priority_all_morphs_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_ALL_MORPHS_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_average_priority_all_morphs_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_ALL_MORPHS_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_total_priority_learning_morphs_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_TOTAL_PRIORITY_LEARNING_MORPHS_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_average_priority_learning_morphs_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_AVERAGE_PRIORITY_LEARNING_MORPHS_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_all_morphs_target_difference_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_ALL_MORPHS_TARGET_DIFFERENCE_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_learning_morphs_target_difference_weight: int = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LEARNING_MORPHS_TARGET_DIFFERENCE_WEIGHT,
                    expected_type=int,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_all_morphs: int = self._get_config_item(
                key=RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS,
                expected_type=int,
                use_default=is_default,
            )
            self.algorithm_upper_target_all_morphs_coefficient_a: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_A,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_all_morphs_coefficient_b: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_B,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_all_morphs_coefficient_c: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_ALL_MORPHS_COEFFICIENT_C,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_all_morphs: int = self._get_config_item(
                key=RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS,
                expected_type=int,
                use_default=is_default,
            )
            self.algorithm_lower_target_all_morphs_coefficient_a: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_A,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_all_morphs_coefficient_b: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_B,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_all_morphs_coefficient_c: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_ALL_MORPHS_COEFFICIENT_C,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_learning_morphs: int = self._get_config_item(
                key=RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS,
                expected_type=int,
                use_default=is_default,
            )
            self.algorithm_lower_target_learning_morphs: int = self._get_config_item(
                key=RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS,
                expected_type=int,
                use_default=is_default,
            )
            self.algorithm_upper_target_learning_morphs_coefficient_a: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_A,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_learning_morphs_coefficient_b: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_B,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_upper_target_learning_morphs_coefficient_c: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_UPPER_TARGET_LEARNING_MORPHS_COEFFICIENT_C,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_a: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_A,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_b: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_B,
                    expected_type=float,
                    use_default=is_default,
                )
            )
            self.algorithm_lower_target_learning_morphs_coefficient_c: float = (
                self._get_config_item(
                    key=RawConfigKeys.ALGORITHM_LOWER_TARGET_LEARNING_MORPHS_COEFFICIENT_C,
                    expected_type=float,
                    use_default=is_default,
                )
            )

            self.hide_recalc_toolbar: bool = self._get_config_item(
                key=RawConfigKeys.HIDE_RECALC_TOOLBAR,
                expected_type=bool,
                use_default=is_default,
            )

            self.hide_lemma_toolbar: bool = self._get_config_item(
                key=RawConfigKeys.HIDE_LEMMA_TOOLBAR,
                expected_type=bool,
                use_default=is_default,
            )

            self.hide_inflection_toolbar: bool = self._get_config_item(
                key=RawConfigKeys.HIDE_INFLECTION_TOOLBAR,
                expected_type=bool,
                use_default=is_default,
            )

            self.filters: list[AnkiMorphsConfigFilter] = self.get_config_filters(
                is_default
            )

        except AssertionError:
            if not ankimorphs_globals.config_broken:
                show_critical_config_error()
                ankimorphs_globals.config_broken = True

        if (
            ankimorphs_globals.new_config_found
            and not ankimorphs_globals.shown_config_warning
        ):
            show_warning_new_config_items()
            ankimorphs_globals.shown_config_warning = True

    def update(self) -> None:
        # The same AnkiMorphsSettings object is shared many
        # places (SettingsTabs, etc.), and to avoid de-synchronization
        # it is better to update the object rather than creating
        # new objects/updating the references.
        new_config = AnkiMorphsConfig()
        self.__dict__.update(new_config.__dict__)

    def _get_key_sequence_config(
        self,
        key: str,
        expected_type: type,
        use_default: bool,
    ) -> QKeySequence:
        config_item: str = self._get_config_item(key, expected_type, use_default)
        assert isinstance(config_item, str)
        return QKeySequence(config_item)

    def get_config_filters(
        self, is_default: bool = False
    ) -> list[AnkiMorphsConfigFilter]:
        config_filters = self._get_config_item(
            key=RawConfigKeys.FILTERS,
            expected_type=list,
            use_default=is_default,
        )

        filters = []
        for _filter in config_filters:
            am_filter = AnkiMorphsConfigFilter(_filter)
            if not am_filter.has_error:
                filters.append(am_filter)
        return filters

    def _get_config_item(
        self,
        key: str,
        expected_type: type,
        use_default: bool,
        # ) -> str | int | bool | list[FilterTypeAlias] | None:
    ) -> Any:
        """
        Tries to find the config item with the specified key,
        if not found then returns the default value and set
        ankimorphs_globals.ankimorphs_new_config_found = True
        """
        try:
            if use_default is False:
                item = self._config_dict[key]
            else:
                item = self._default_config_dict[key]
        except KeyError:
            ankimorphs_globals.new_config_found = True
            item = self._default_config_dict[key]
        assert isinstance(item, expected_type)
        return item


def get_config_dict() -> dict[str, Any]:
    assert mw is not None
    config_dict: dict[str, Any] | None = mw.addonManager.getConfig(__name__)
    assert config_dict is not None
    return config_dict


def get_all_defaults_config_dict() -> dict[str, Any]:
    assert mw is not None
    addon = mw.addonManager.addonFromModule(__name__)  # necessary to prevent anki bug
    default_config_dict: dict[str, Any] | None = mw.addonManager.addonConfigDefaults(
        addon
    )
    assert default_config_dict is not None
    return default_config_dict


def load_stored_am_configs(
    stored_config: dict[str, str | int | float | bool | object]
) -> None:
    """
    This function loads the stored dict found in 'ankimorphs_profile_settings.json' and
    then merges any new entries found in the default config.
    """
    assert mw is not None

    merged_configs = get_all_defaults_config_dict()
    assert merged_configs is not None

    try:
        for key, value in stored_config.items():
            merged_configs[key] = value
    except KeyError:
        # this happens when backwards compatibility has been broken
        # and keys no longer exists in the default config
        pass

    # write the merged configs to 'meta.json', i.e. the config Anki uses.
    mw.addonManager.writeConfig(__name__, merged_configs)


def update_configs(new_configs: dict[str, str | int | float | bool | object]) -> None:
    assert mw is not None
    config = mw.addonManager.getConfig(__name__)
    assert config is not None

    for key, value in new_configs.items():
        config[key] = value

    mw.addonManager.writeConfig(__name__, config)
    save_config_to_am_file(config)


def save_config_to_am_file(
    configs: dict[str, str | int | float | bool | object]
) -> None:
    assert mw is not None
    profile_settings_path = Path(
        mw.pm.profileFolder(), ankimorphs_globals.PROFILE_SETTINGS_FILE_NAME
    )
    with open(profile_settings_path, mode="w", encoding="utf-8") as file:
        json.dump(configs, file, sort_keys=True)


def reset_all_configs() -> None:
    assert mw is not None
    default_configs = get_all_defaults_config_dict()
    mw.addonManager.writeConfig(__name__, default_configs)  # updates 'meta.json'

    assert default_configs is not None
    save_config_to_am_file(default_configs)


def get_read_enabled_filters() -> list[AnkiMorphsConfigFilter]:
    config_filters = AnkiMorphsConfig().get_config_filters()
    assert isinstance(config_filters, list)

    read_filters = []
    for config_filter in config_filters:
        if config_filter.read:
            read_filters.append(config_filter)
    return read_filters


def get_modify_enabled_filters() -> list[AnkiMorphsConfigFilter]:
    config_filters = AnkiMorphsConfig().get_config_filters()
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


def show_critical_config_error() -> None:
    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle("AnkiMorphs Error")
    critical_box.setIcon(QMessageBox.Icon.Critical)
    ok_button: QPushButton = QPushButton("OK")
    critical_box.addButton(ok_button, QMessageBox.ButtonRole.YesRole)
    body: str = (
        "**Unexpected config type!**"
        "<br/><br/>"
        "The saved configs are malformed and will cause exceptions if left as is."
        "<br/><br/>"
        "Please do the following:\n"
        "1. Restart Anki without add-ons (hold shift key while opening Anki)\n"
        "2. Restore the default configs of 'AnkiMorphs' (and 'ankimorphs' if you have that)\n\n"
        "    Tools -> add-ons -> select add-on -> config -> restore defaults\n"
        "3. Delete the 'ankimorphs_profile_settings.json' file in the Anki profile folder\n"
        "4. Restart Anki\n\n"
    )
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    critical_box.setText(body)
    critical_box.exec()


def show_warning_new_config_items() -> None:
    critical_box = QMessageBox(mw)
    critical_box.setWindowTitle("AnkiMorphs Warning")
    critical_box.setIcon(QMessageBox.Icon.Warning)
    body: str = (
        "**New AnkiMorphs settings detected!**"
        "<br/><br/>"
        "New settings have been added "
        "(<a href='https://github.com/mortii/anki-morphs/releases'>changelog</a>), "
        "which may affect how AnkiMorphs performs."
        "<br/><br/>"
        "To ensure optimal performance, please follow these steps:<br/>"
        "1. Open the AnkiMorphs settings menu.<br/>"
        "2. Review and adjust the settings as needed.<br/>"
        "3. Apply the settings.<br/>"
        "4. Recalc"
    )
    critical_box.setTextFormat(Qt.TextFormat.MarkdownText)
    critical_box.setText(body)
    critical_box.exec()
