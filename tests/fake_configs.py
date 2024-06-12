import copy
import json
from pathlib import Path
from typing import Any

from ankimorphs import ankimorphs_globals

DEFAULT_CONFIG_PATH = Path("ankimorphs", "config.json")

default_config_dict: dict[str, Any]

with open(DEFAULT_CONFIG_PATH, encoding="utf-8") as _file:
    default_config_dict = json.load(_file)

default_config_dict["filters"][0]["extra_highlighted"] = True
default_config_dict["filters"][0]["extra_score"] = True
default_config_dict["filters"][0]["extra_unknowns"] = True
default_config_dict["filters"][0]["extra_unknowns_count"] = True
default_config_dict["filters"][0]["extra_score_terms"] = True
default_config_dict["filters"][0]["field_index"] = 0
default_config_dict["filters"][0]["morph_priority"] = "Collection frequency"
default_config_dict["filters"][0]["morph_priority_index"] = 0

# print("default config dict:")
# pprint.pp(default_config_dict)

################################################################
#             big_japanese_collection config
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
#             offset_enabled config
################################################################
#
#
#
################################################################
config_offset_enabled = copy.deepcopy(default_config_dict)
config_offset_enabled["recalc_offset_new_cards"] = True
config_offset_enabled["filters"][0]["note_type"] = "note-type-with-offset"
config_offset_enabled["filters"][0]["field"] = "Front"
config_offset_enabled["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Language w/ Spaces"


################################################################
#             known_morphs_enabled config
################################################################
#
#
#
################################################################
config_known_morphs_enabled = copy.deepcopy(default_config_dict)
config_known_morphs_enabled["recalc_read_known_morphs_folder"] = True
config_known_morphs_enabled["recalc_move_known_new_cards_to_the_end"] = False
config_known_morphs_enabled["filters"][0]["note_type"] = "known-morphs-note-type"
config_known_morphs_enabled["filters"][0]["field"] = "Front"
config_known_morphs_enabled["filters"][0][
    "morphemizer_description"
] = "AnkiMorphs: Language w/ Spaces"


################################################################
#             lemma_priority config
################################################################
# Matches the "lemma_priority_collection.anki2" collection
#
################################################################
config_lemma_priority = copy.deepcopy(default_config_dict)
config_lemma_priority["filters"][0]["note_type"] = "Basic"
config_lemma_priority["filters"][0]["field"] = "Front"
config_lemma_priority["filters"][0]["morphemizer_description"] = "spaCy: en_core_web_sm"
config_lemma_priority["algorithm_inflection_priority"] = False
config_lemma_priority["algorithm_lemma_priority"] = True


################################################################
#             inflection_priority config
################################################################
# The inverse of "config_lemma_priority"
################################################################
config_inflection_priority = copy.deepcopy(config_lemma_priority)
config_inflection_priority["algorithm_inflection_priority"] = True
config_inflection_priority["algorithm_lemma_priority"] = False


################################################################
#             ignore_names_txt_enabled config
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
#             wrong_note_type config
################################################################
#
#
#
################################################################
config_wrong_note_type = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_note_type["filters"][0]["note_type"] = "random_wrong_value"

################################################################
#             wrong_field_name config
################################################################
#
#
#
################################################################
config_wrong_field_name = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_field_name["filters"][0]["field"] = "random_wrong_value"

################################################################
#             wrong_morph_priority config
################################################################
#
#
#
################################################################
config_wrong_morph_priority = copy.deepcopy(config_ignore_names_txt_enabled)
config_wrong_morph_priority["filters"][0]["morph_priority"] = "random_wrong_value"

################################################################
#             wrong_morphemizer_description config
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
#             default_note_type config
################################################################
#
#
#
################################################################
config_default_note_type = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_note_type["filters"][0]["note_type"] = ankimorphs_globals.NONE_OPTION

################################################################
#             default_field config
################################################################
#
#
#
################################################################
config_default_field = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_field["filters"][0]["field"] = ankimorphs_globals.NONE_OPTION


################################################################
#             default_morph_priority config
################################################################
#
#
#
################################################################
config_default_morph_priority = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_morph_priority["filters"][0][
    "morph_priority"
] = ankimorphs_globals.NONE_OPTION


################################################################
#             default_morph_priority config
################################################################
#
#
#
################################################################
config_default_morphemizer = copy.deepcopy(config_ignore_names_txt_enabled)
config_default_morphemizer["filters"][0][
    "morphemizer_description"
] = ankimorphs_globals.NONE_OPTION
