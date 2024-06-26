import copy
import json
from pathlib import Path
from typing import Any

from ankimorphs import ankimorphs_globals

DEFAULT_CONFIG_PATH = Path("ankimorphs", "config.json")

default_config_dict: dict[str, Any]

with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as _file:
    default_config_dict = json.load(_file)

default_config_dict["filters"][0]["note_type"] = "Basic"
default_config_dict["filters"][0]["field"] = "Front"
default_config_dict["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Language w/ Spaces"
default_config_dict["filters"][0]["extra_highlighted"] = True
default_config_dict["filters"][0]["extra_score"] = True
default_config_dict["filters"][0]["extra_unknowns"] = True
default_config_dict["filters"][0]["extra_unknowns_count"] = True
default_config_dict["filters"][0]["extra_score_terms"] = True
default_config_dict["filters"][0]["field_index"] = 0
default_config_dict["filters"][0]["morph_priority_selection"] = "Collection frequency"


# print("default config dict:")
# pprint.pp(default_config_dict)

################################################################
#             config_big_japanese_collection
################################################################
#
#
#
################################################################
config_big_japanese_collection = copy.deepcopy(default_config_dict)
config_big_japanese_collection["preprocess_ignore_bracket_contents"] = True
config_big_japanese_collection["preprocess_ignore_names_morphemizer"] = True
config_big_japanese_collection["preprocess_ignore_round_bracket_contents"] = True
config_big_japanese_collection["preprocess_ignore_slim_round_bracket_contents"] = True
config_big_japanese_collection["filters"][0]["note_type"] = "japanese_sub2srs"
config_big_japanese_collection["filters"][0]["field"] = "Japanese"
config_big_japanese_collection["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Japanese"


################################################################
#             config_offset_inflection_enabled
################################################################
# Matches `offset_new_cards_inflection_collection.anki2`.
# Evaluates morphs by inflection.
################################################################
config_offset_inflection_enabled = copy.deepcopy(default_config_dict)
config_offset_inflection_enabled["filters"][0][
    "morphemizer_description"
] = "spaCy: en_core_web_sm"
config_offset_inflection_enabled["recalc_offset_new_cards"] = True

################################################################
#             config_offset_lemma_enabled
################################################################
# Matches `offset_new_cards_lemma_collection.anki2`.
# Evaluates morphs by lemma.
################################################################
config_offset_lemma_enabled = copy.deepcopy(config_offset_inflection_enabled)
config_offset_lemma_enabled["evaluate_morph_inflection"] = False
config_offset_lemma_enabled["evaluate_morph_lemma"] = True


################################################################
#             config_known_morphs_enabled
################################################################
#
#
#
################################################################
config_known_morphs_enabled = copy.deepcopy(default_config_dict)
config_known_morphs_enabled["recalc_read_known_morphs_folder"] = True
config_known_morphs_enabled["read_known_morphs_folder"] = False
config_known_morphs_enabled["filters"][0]["note_type"] = "known-morphs-note-type"
config_known_morphs_enabled["filters"][0]["field"] = "Front"
config_known_morphs_enabled["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Language w/ Spaces"


################################################################
#             config_lemma_priority
################################################################
# Matches the "lemma_priority_collection.anki2" collection.
################################################################
config_lemma_priority = copy.deepcopy(default_config_dict)
config_lemma_priority["filters"][0]["morphemizer_description"] = "spaCy: en_core_web_sm"
config_lemma_priority["evaluate_morph_inflection"] = False
config_lemma_priority["evaluate_morph_lemma"] = True


################################################################
#             config_inflection_priority
################################################################
# The inverse of "config_lemma_priority"
################################################################
config_inflection_priority = copy.deepcopy(config_lemma_priority)
config_inflection_priority["evaluate_morph_inflection"] = True
config_inflection_priority["evaluate_morph_lemma"] = False


################################################################
#            config_ignore_names_txt_enabled
################################################################
#
#
#
################################################################
config_ignore_names_txt_enabled = copy.deepcopy(default_config_dict)
config_ignore_names_txt_enabled["preprocess_ignore_names_textfile"] = True
config_ignore_names_txt_enabled["filters"][0]["note_type"] = "note-type-with-names"
config_ignore_names_txt_enabled["filters"][0]["field"] = "Front"
config_ignore_names_txt_enabled["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Language w/ Spaces"


################################################################
#             config_wrong_note_type
################################################################
#
#
#
################################################################
config_wrong_note_type = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_note_type["filters"][0]["note_type"] = "random_wrong_value"

################################################################
#             config_wrong_field_name
################################################################
#
#
#
################################################################
config_wrong_field_name = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_field_name["filters"][0]["field"] = "random_wrong_value"

################################################################
#            config_wrong_morph_priority
################################################################
#
#
#
################################################################
config_wrong_morph_priority = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_morph_priority["filters"][0][
    "morph_priority_selection"
] = "random_wrong_value"

################################################################
#             config_wrong_morphemizer_description
################################################################
#
#
#
################################################################
config_wrong_morphemizer_description = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_morphemizer_description["filters"][0][
    "morphemizer_description"
] = "random_wrong_value"

################################################################
#             config_default_note_type
################################################################
#
#
#
################################################################
config_default_note_type = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_note_type["filters"][0]["note_type"] = ankimorphs_globals.NONE_OPTION

################################################################
#             config_default_field
################################################################
#
#
#
################################################################
config_default_field = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_field["filters"][0]["field"] = ankimorphs_globals.NONE_OPTION


################################################################
#            config_default_morph_priority
################################################################
#
#
#
################################################################
config_default_morph_priority = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_morph_priority["filters"][0][
    "morph_priority_selection"
] = ankimorphs_globals.NONE_OPTION


################################################################
#             config_default_morphemizer
################################################################
#
#
#
################################################################
config_default_morphemizer = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_morphemizer["filters"][0][
    "morphemizer_description"
] = ankimorphs_globals.NONE_OPTION
