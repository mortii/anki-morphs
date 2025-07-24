class General:
    ANKIMORPHS_VERSION = "ankimorphs_version"


class Dialogs:
    GENERATORS_WINDOW = "generators_window"
    KNOWN_MORPHS_EXPORTER = "known_morphs_exporter"
    SPACY_MANAGER_WINDOW = "spacy_manager_window"
    PROGRESSION_WINDOW = "progression_window"
    GENERATOR_OUTPUT_PRIORITY_FILE = "generator_output_priority_file"
    GENERATOR_OUTPUT_STUDY_PLAN = "generator_output_study_plan"


class GeneratorsWindowKeys:
    WINDOW_GEOMETRY = "window_geometry"
    MORPHEMIZER = "morphemizer"
    FILE_FORMATS = "file_formats"
    PREPROCESS = "preprocess"
    INPUT_DIR = "input_dir"


class FileFormatsKeys:
    ASS = "ass"
    EPUB = "epub"
    HTML = "html"
    MD = "md"
    SRT = "srt"
    TXT = "txt"
    VTT = "vtt"


class PreprocessKeys:
    IGNORE_SQUARE_BRACKETS = "ignore_square_brackets"
    IGNORE_ROUND_BRACKETS = "ignore_round_brackets"
    IGNORE_SLIM_ROUND_BRACKETS = "ignore_slim_round_brackets"
    IGNORE_NAMES_MORPHEMIZER = "ignore_names_morphemizer"
    IGNORE_NAMES_IN_FILE = "ignore_names_in_file"
    IGNORE_NUMBERS = "ignore_numbers"
    IGNORE_CUSTOM_CHARS = "ignore_custom_chars"
    CHARS_TO_IGNORE = "chars_to_ignore"


class KnownMorphsExporterKeys:
    WINDOW_GEOMETRY = "window_geometry"
    OUTPUT_DIR = "output_dir"
    LEMMA = "lemma"
    INFLECTION = "inflection"
    INTERVAL = "interval"
    OCCURRENCES = "occurrences"


class SpacyManagerWindowKeys:
    WINDOW_GEOMETRY = "window_geometry"


class ProgressionWindowKeys:
    WINDOW_GEOMETRY = "window_geometry"
    PRIORITY_FILE = "priority_file"
    LEMMA_EVALUATION = "lemma_evaluation"
    INFLECTION_EVALUATION = "inflection_evaluation"
    PRIORITY_RANGE_START = "priority_range_start"
    PRIORITY_RANGE_END = "priority_range_end"
    BIN_SIZE = "bin_size"
    BIN_TYPE_NORMAL = "bin_type_normal"
    BIN_TYPE_CUMULATIVE = "bin_type_cumulative"


class GeneratorsOutputKeys:
    WINDOW_GEOMETRY = "window_geometry"
    LEMMA_FORMAT = "lemma_format"
    OUTPUT_FILE_PATH = "output_file_path"
    INFLECTION_FORMAT = "inflection_format"
    MIN_OCCURRENCE_SELECTED = "min_occurrence_selected"
    MIN_OCCURRENCE_CUTOFF = "min_occurrence_cutoff"
    COMPREHENSION_SELECTED = "comprehension_selected"
    COMPREHENSION_CUTOFF = "comprehension_cutoff"
    OCCURRENCES_COLUMN_SELECTED = "occurrences_column_selected"
