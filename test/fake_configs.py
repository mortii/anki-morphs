import copy
import json
from pathlib import Path
from typing import Any

from ankimorphs import ankimorphs_globals as am_globals
from ankimorphs.ankimorphs_config import RawConfigFilterKeys as FilterKeys
from ankimorphs.ankimorphs_config import RawConfigKeys as ConfigKeys

DEFAULT_CONFIG_PATH = Path("ankimorphs", "config.json")

default_config_dict: dict[str, Any]

with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as _file:
    default_config_dict = json.load(_file)

default_config_filter = default_config_dict[ConfigKeys.FILTERS][0]
default_config_filter[FilterKeys.NOTE_TYPE] = "Basic"
default_config_filter[FilterKeys.FIELD] = "Front"
default_config_filter[FilterKeys.MORPHEMIZER_DESCRIPTION] = (
    "AnkiMorphs: Simple Space Splitter"
)
default_config_filter[FilterKeys.EXTRA_ALL_MORPHS] = True
default_config_filter[FilterKeys.EXTRA_ALL_MORPHS_COUNT] = True
default_config_filter[FilterKeys.EXTRA_HIGHLIGHTED] = True
default_config_filter[FilterKeys.EXTRA_SCORE] = True
default_config_filter[FilterKeys.EXTRA_SCORE_TERMS] = True
default_config_filter[FilterKeys.EXTRA_STUDY_MORPHS] = True
default_config_filter[FilterKeys.EXTRA_UNKNOWN_MORPHS] = True
default_config_filter[FilterKeys.EXTRA_UNKNOWN_MORPHS_COUNT] = True
default_config_filter[FilterKeys.MORPH_PRIORITY_SELECTION] = "Collection frequency"


# print("default config dict:")
# pprint.pp(default_config_dict)

################################################################
#                   config_lemma_evaluation
################################################################
# Evaluates morphs by lemma.
################################################################
# fmt: off
config_lemma_evaluation = copy.deepcopy(default_config_dict)
config_lemma_evaluation[ConfigKeys.EVALUATE_MORPH_INFLECTION] = False
config_lemma_evaluation[ConfigKeys.EVALUATE_MORPH_LEMMA] = True
# fmt: on


################################################################
#           config_lemma_evaluation_ignore_brackets
################################################################
# Evaluates morphs by lemma, ignores bracket contents.
################################################################
# fmt: off
config_lemma_evaluation_ignore_brackets = copy.deepcopy(config_lemma_evaluation)
config_lemma_evaluation_ignore_brackets[ConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS] = True
# fmt: on


################################################################
#             config_known_morphs_enabled
################################################################
# Matches `known-morphs-collection.anki2`.
################################################################
# fmt: off
config_known_morphs_enabled = copy.deepcopy(default_config_dict)
config_known_morphs_enabled[ConfigKeys.READ_KNOWN_MORPHS_FOLDER] = True
config_known_morphs_enabled[ConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS] = True
config_known_morphs_enabled[ConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE] = (
    ",.!"
)
# fmt: on

################################################################
#        config_lemma_evaluation_lemma_extra_fields
################################################################
# Matches "lemma_evaluation_lemma_extra_fields_collection.anki2".
################################################################
# fmt: off
config_lemma_evaluation_lemma_extra_fields = copy.deepcopy(default_config_dict)
config_lemma_evaluation_lemma_extra_fields[ConfigKeys.EVALUATE_MORPH_INFLECTION] = False
config_lemma_evaluation_lemma_extra_fields[ConfigKeys.EVALUATE_MORPH_LEMMA] = True
config_lemma_evaluation_lemma_extra_fields[ConfigKeys.EXTRA_FIELDS_DISPLAY_LEMMAS] = True
config_lemma_evaluation_lemma_extra_fields[ConfigKeys.EXTRA_FIELDS_DISPLAY_INFLECTIONS] = False

config_lemma_evaluation_lemma_extra_fields[ConfigKeys.FILTERS][0][
    FilterKeys.MORPHEMIZER_DESCRIPTION
] = "spaCy: en_core_web_sm"
# fmt: on


################################################################
#             config_inflection_evaluation
################################################################
# The inverse of "config_lemma_evaluation_lemma_extra_fields"
################################################################
config_inflection_evaluation = copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
config_inflection_evaluation[ConfigKeys.EVALUATE_MORPH_INFLECTION] = True
config_inflection_evaluation[ConfigKeys.EVALUATE_MORPH_LEMMA] = False


################################################################
#             config_offset_lemma_enabled
################################################################
# Matches `offset_new_cards_lemma_collection.anki2`.
# Evaluates morphs by lemma.
################################################################
config_offset_lemma_enabled = copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
config_offset_lemma_enabled[ConfigKeys.RECALC_OFFSET_NEW_CARDS] = True


################################################################
#               config_dont_skip_fresh_morphs
################################################################
# Used with: `card_handling_collection.anki2`.
################################################################
# fmt: off
config_dont_skip_fresh_morphs = copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
config_dont_skip_fresh_morphs[ConfigKeys.SKIP_DONT_WHEN_CONTAINS_FRESH_MORPHS] = True
config_dont_skip_fresh_morphs[ConfigKeys.SKIP_WHEN_CONTAINS_FRESH_MORPHS] = False
# fmt: on

################################################################
#             config_disabled_skip_no_unknown_morphs
################################################################
# Used with: `card_handling_collection.anki2`.
################################################################
# fmt: off
config_disabled_skip_no_unknown_morphs = copy.deepcopy(config_lemma_evaluation_lemma_extra_fields)
config_disabled_skip_no_unknown_morphs[ConfigKeys.SKIP_NO_UNKNOWN_MORPHS] = False
# fmt: on

################################################################
#             config_offset_inflection_enabled
################################################################
# Matches `offset_new_cards_inflection_collection.anki2`.
# Evaluates morphs by inflection.
################################################################
# fmt: off
config_offset_inflection_enabled = copy.deepcopy(default_config_dict)
config_offset_inflection_enabled[ConfigKeys.RECALC_OFFSET_NEW_CARDS] = True
# fmt: on


################################################################
#            config_ignore_names_txt_enabled
################################################################
# Matches "ignore_names_txt_collection.anki2".
################################################################
config_ignore_names_txt_enabled = copy.deepcopy(default_config_dict)
config_ignore_names_txt_enabled[ConfigKeys.PREPROCESS_IGNORE_NAMES_TEXTFILE] = True


################################################################
#             config_big_japanese_collection
################################################################
# Matches `big_japanese_collection.anki2`
################################################################
# fmt: off
config_big_japanese_collection = copy.deepcopy(default_config_dict)
config_big_japanese_collection[ConfigKeys.PREPROCESS_IGNORE_BRACKET_CONTENTS] = True
config_big_japanese_collection[ConfigKeys.PREPROCESS_IGNORE_NAMES_MORPHEMIZER] = True
config_big_japanese_collection[ConfigKeys.PREPROCESS_IGNORE_ROUND_BRACKET_CONTENTS] = True
config_big_japanese_collection[ConfigKeys.PREPROCESS_IGNORE_SLIM_ROUND_BRACKET_CONTENTS] = True

config_big_japanese_collection_filter = config_big_japanese_collection[ConfigKeys.FILTERS][0]
config_big_japanese_collection_filter[FilterKeys.NOTE_TYPE] = "japanese_sub2srs"
config_big_japanese_collection_filter[FilterKeys.FIELD] = "Japanese"
config_big_japanese_collection_filter[FilterKeys.MORPHEMIZER_DESCRIPTION] = "AnkiMorphs: Japanese"
# fmt: on


################################################################
#          config_use_stability_for_known_threshold
################################################################
# Matches `card_stability_collection.anki2`.
################################################################
# fmt: off
config_use_stability_for_known_threshold = copy.deepcopy(default_config_dict)
config_use_stability_for_known_threshold[ConfigKeys.USE_STABILITY_FOR_KNOWN_THRESHOLD] = True

config_use_stability_for_known_threshold_filter = config_use_stability_for_known_threshold[ConfigKeys.FILTERS][0]
config_use_stability_for_known_threshold_filter[FilterKeys.NOTE_TYPE] = "japanese_sub2srs"
config_use_stability_for_known_threshold_filter[FilterKeys.FIELD] = "Japanese"
config_use_stability_for_known_threshold_filter[FilterKeys.MORPHEMIZER_DESCRIPTION] = "AnkiMorphs: Japanese"
# fmt: on

################################################################
#          config_use_interval_for_known_threshold
################################################################
# Matches `card_interval_collection.anki2`.
################################################################
# fmt: off
config_use_interval_for_known_threshold = copy.deepcopy(config_use_stability_for_known_threshold)
config_use_interval_for_known_threshold[ConfigKeys.USE_STABILITY_FOR_KNOWN_THRESHOLD] = False
# fmt: on


################################################################
#                 config_max_morph_priority
################################################################
# Matches `max_morph_priority_collection.anki2`
################################################################
# fmt: off
config_max_morph_priority = copy.deepcopy(default_config_dict)
config_max_morph_priority_filter = config_max_morph_priority[ConfigKeys.FILTERS][0]
config_max_morph_priority_filter[FilterKeys.MORPHEMIZER_DESCRIPTION] = "spaCy: ja_core_news_sm"
config_max_morph_priority_filter[FilterKeys.MORPH_PRIORITY_SELECTION] = "ja_core_news_sm_freq_inflection_min_occurrence.csv"
# fmt: on

################################################################
#               config_suspend_morphs_known
################################################################
# Matches `suspend_all_morphs_known.anki2`
################################################################
# fmt: off
config_suspend_morphs_known = copy.deepcopy(default_config_dict)
config_suspend_morphs_known[ConfigKeys.RECALC_SUSPEND_NEW_CARDS] = am_globals.ONLY_KNOWN_OPTION
# fmt: on

################################################################
#            config_suspend_morphs_known_or_fresh
################################################################
# Matches `suspend_morphs_known_or_fresh.anki2`
################################################################
# fmt: off
config_suspend_morphs_known_or_fresh = copy.deepcopy(default_config_dict)
config_suspend_morphs_known_or_fresh[ConfigKeys.RECALC_SUSPEND_NEW_CARDS] = am_globals.ONLY_KNOWN_OR_FRESH_OPTION
# fmt: on


################################################################
#              config_move_to_end_morphs_known
################################################################
# Matches `move_to_end_morphs_known.anki2`
################################################################
# fmt: off
config_move_to_end_morphs_known = copy.deepcopy(default_config_dict)
config_move_to_end_morphs_known[ConfigKeys.RECALC_MOVE_NEW_CARDS_TO_THE_END] = am_globals.ONLY_KNOWN_OPTION
# fmt: on

################################################################
#            config_move_to_end_morphs_known_or_fresh
################################################################
# Matches `move_to_end_morphs_known_or_fresh.anki2`
################################################################
# fmt: off
config_move_to_end_morphs_known_or_fresh = copy.deepcopy(default_config_dict)
config_move_to_end_morphs_known_or_fresh[ConfigKeys.RECALC_MOVE_NEW_CARDS_TO_THE_END] = am_globals.ONLY_KNOWN_OR_FRESH_OPTION
# fmt: on


################################################################
#             config_wrong_note_type
################################################################
# Works with any arbitrary collection and db
################################################################
config_wrong_note_type = copy.deepcopy(default_config_dict)
config_wrong_note_type[ConfigKeys.FILTERS][0][
    FilterKeys.NOTE_TYPE
] = "random_wrong_value"


################################################################
#             config_wrong_field_name
################################################################
# Works with any arbitrary collection and db
################################################################
config_wrong_field_name = copy.deepcopy(default_config_dict)
config_wrong_field_name[ConfigKeys.FILTERS][0][FilterKeys.FIELD] = "random_wrong_value"


################################################################
#            config_wrong_morph_priority
################################################################
# Works with any arbitrary collection and db
################################################################
config_wrong_morph_priority = copy.deepcopy(default_config_dict)
config_wrong_morph_priority[ConfigKeys.FILTERS][0][
    FilterKeys.MORPH_PRIORITY_SELECTION
] = "random_wrong_value"


################################################################
#             config_wrong_morphemizer_description
################################################################
# Works with any arbitrary collection and db
################################################################
config_wrong_morphemizer_description = copy.deepcopy(default_config_dict)
config_wrong_morphemizer_description[ConfigKeys.FILTERS][0][
    FilterKeys.MORPHEMIZER_DESCRIPTION
] = "random_wrong_value"


################################################################
#             config_default_note_type
################################################################
# Works with any arbitrary collection and db
################################################################
config_default_note_type = copy.deepcopy(default_config_dict)
config_default_note_type[ConfigKeys.FILTERS][0][
    FilterKeys.NOTE_TYPE
] = am_globals.NONE_OPTION


################################################################
#             config_default_field
################################################################
# Works with any arbitrary collection and db
################################################################
config_default_field = copy.deepcopy(default_config_dict)
config_default_field[ConfigKeys.FILTERS][0][FilterKeys.FIELD] = am_globals.NONE_OPTION


################################################################
#            config_default_morph_priority
################################################################
# Works with any arbitrary collection and db
################################################################
config_default_morph_priority = copy.deepcopy(default_config_dict)
config_default_morph_priority[ConfigKeys.FILTERS][0][
    FilterKeys.MORPH_PRIORITY_SELECTION
] = am_globals.NONE_OPTION


################################################################
#             config_default_morphemizer
################################################################
# Works with any arbitrary collection and db
################################################################
config_default_morphemizer = copy.deepcopy(default_config_dict)
config_default_morphemizer[ConfigKeys.FILTERS][0][
    FilterKeys.MORPHEMIZER_DESCRIPTION
] = am_globals.NONE_OPTION

################################################################
#             config_ignoring_custom_characters
################################################################
# Works with any arbitrary collection and db
################################################################
config_ignoring_custom_characters = copy.deepcopy(default_config_dict)
config_ignoring_custom_characters[ConfigKeys.PREPROCESS_IGNORE_CUSTOM_CHARACTERS] = True
config_ignoring_custom_characters[ConfigKeys.PREPROCESS_CUSTOM_CHARACTERS_TO_IGNORE] = (
    ",.?"
)
