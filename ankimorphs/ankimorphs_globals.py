"""
This file contains constants and variables that are used across multiple files.
If a constants or a variable is only used in one file, then it should be declared in
that file and not here.
"""

__version__ = "2.2.4"

DEV_MODE: bool = False

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

NONE_OPTION = "(none)"
COLLECTION_FREQUENCY_OPTION = "Collection frequency"


ankimorphs_broken: bool = False
