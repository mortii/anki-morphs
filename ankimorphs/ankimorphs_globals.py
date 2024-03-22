"""
This file contains constants and variables that are used across multiple files.
If a constants or a variable is only used in one file, then it should be declared in
that file and not here.
"""

DEV_MODE: bool = False

PROFILE_SETTINGS_FILE_NAME = "ankimorphs_profile_settings.json"

SETTINGS_DIALOG_NAME: str = "am_settings_dialog"
TAG_SELECTOR_DIALOG_NAME: str = "am_tag_selector_dialog"
FREQUENCY_FILE_GENERATOR_DIALOG_NAME: str = "am_frequency_file_dialog"
READABILITY_REPORT_GENERATOR_DIALOG_NAME: str = "am_readability_report_dialog"
KNOWN_MORPHS_EXPORTER_DIALOG_NAME: str = "am_known_morphs_exporter_dialog"

EXTRA_FIELD_UNKNOWNS: str = "am-unknowns"
EXTRA_FIELD_UNKNOWNS_COUNT: str = "am-unknowns-count"
EXTRA_FIELD_HIGHLIGHTED: str = "am-highlighted"
EXTRA_FIELD_SCORE: str = "am-score"

ankimorphs_broken: bool = False
