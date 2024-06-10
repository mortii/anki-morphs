"""
This file contains constants and variables that are used across multiple files.
If a constants or a variable is only used in one file, then it should be declared in
that file and not here.
"""

__version__ = "3.0.0-testing-3"

DEV_MODE: bool = True

PROFILE_SETTINGS_FILE_NAME = "ankimorphs_profile_settings.json"
NAMES_TXT_FILE_NAME = "names.txt"
KNOWN_MORPHS_DIR_NAME = "known-morphs"
FREQUENCY_FILES_DIR_NAME = "frequency-files"

SETTINGS_DIALOG_NAME: str = "am_settings_dialog"
TAG_SELECTOR_DIALOG_NAME: str = "am_tag_selector_dialog"
GENERATOR_DIALOG_NAME: str = "am_generator_dialog"
KNOWN_MORPHS_EXPORTER_DIALOG_NAME: str = "am_known_morphs_exporter_dialog"

EXTRA_FIELD_UNKNOWNS: str = "am-unknowns"
EXTRA_FIELD_UNKNOWNS_COUNT: str = "am-unknowns-count"
EXTRA_FIELD_HIGHLIGHTED: str = "am-highlighted"
EXTRA_FIELD_SCORE: str = "am-score"
EXTRA_FIELD_SCORE_TERMS: str = "am-score-terms"

# Morph priority options in the note filter settings
NONE_OPTION = "(none)"
COLLECTION_FREQUENCY_OPTION = "Collection frequency"

# Frequency file/study plan headers
LEMMA_HEADER = "Morph-Lemma"
INFLECTION_HEADER = "Morph-Inflection"
LEMMA_PRIORITY_HEADER = "Lemma-Priority"
INFLECTION_PRIORITY_HEADER = "Inflection-Priority"
OCCURRENCES_HEADER = "Occurrences"

ankimorphs_broken: bool = False
