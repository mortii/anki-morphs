"""
This file contains constants and variables that are used across multiple files.
If a constants or a variable is only used in one file, then it should be declared in
that file and not here.
"""

# Semantic Versioning https://semver.org/
__version__ = "3.0.0-testing-4"

DEV_MODE: bool = True

PROFILE_SETTINGS_FILE_NAME = "ankimorphs_profile_settings.json"
NAMES_TXT_FILE_NAME = "names.txt"
KNOWN_MORPHS_DIR_NAME = "known-morphs"
FREQUENCY_FILES_DIR_NAME = "frequency-files"

SETTINGS_DIALOG_NAME: str = "am_settings_dialog"
TAG_SELECTOR_DIALOG_NAME: str = "am_tag_selector_dialog"
GENERATOR_DIALOG_NAME: str = "am_generator_dialog"
PROGRESSION_DIALOG_NAME: str = "am_progression_dialog"
KNOWN_MORPHS_EXPORTER_DIALOG_NAME: str = "am_known_morphs_exporter_dialog"

# The static names of the extra fields
EXTRA_FIELD_ALL_MORPHS: str = "am-all-morphs"
EXTRA_FIELD_ALL_MORPHS_COUNT: str = "am-all-morphs-count"
EXTRA_FIELD_UNKNOWN_MORPHS: str = "am-unknown-morphs"
EXTRA_FIELD_UNKNOWN_MORPHS_COUNT: str = "am-unknown-morphs-count"
EXTRA_FIELD_HIGHLIGHTED: str = "am-highlighted"
EXTRA_FIELD_SCORE: str = "am-score"
EXTRA_FIELD_SCORE_TERMS: str = "am-score-terms"
EXTRA_FIELD_STUDY_MORPHS: str = "am-study-morphs"

# Morph priority options in the note filter settings
NONE_OPTION = "(none)"
COLLECTION_FREQUENCY_OPTION = "Collection frequency"

# Frequency file/study plan headers
LEMMA_HEADER = "Morph-Lemma"
INFLECTION_HEADER = "Morph-Inflection"
LEMMA_PRIORITY_HEADER = "Lemma-Priority"
INFLECTION_PRIORITY_HEADER = "Inflection-Priority"
OCCURRENCES_HEADER = "Occurrences"

config_broken: bool = False
new_config_found: bool = False
shown_config_warning: bool = False
