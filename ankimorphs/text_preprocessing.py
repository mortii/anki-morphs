import re
from typing import Any

from . import name_file_utils
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme

square_brackets_regex = re.compile(r"\[[^]]*]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^)]*\)")

translation_table: dict[int, Any] = {}


def update_translation_table() -> None:
    """
    The translation table is a dict of which characters to we want
    to remove from the text when preprocessing.

    Note: this function is executed on startup and when settings are saved
    """
    global translation_table
    translation_table = str.maketrans(
        "", "", AnkiMorphsConfig().preprocess_custom_characters_to_ignore
    )


def get_processed_text(am_config: AnkiMorphsConfig, text: str) -> str:
    if am_config.preprocess_ignore_bracket_contents:
        text = square_brackets_regex.sub("", text)

    if am_config.preprocess_ignore_round_bracket_contents:
        text = round_brackets_regex.sub("", text)

    if am_config.preprocess_ignore_slim_round_bracket_contents:
        text = slim_round_brackets_regexp.sub("", text)

    if am_config.preprocess_ignore_numbers:
        text = re.sub(r"\d", "", text)

    if am_config.preprocess_ignore_custom_characters:
        # str.translate() removes characters in a single pass, which is
        # much more efficient than str.replace()
        text = text.translate(translation_table)

    return text


def remove_names_textfile(morphs: list[Morpheme]) -> list[Morpheme]:
    names = name_file_utils.get_names_from_file()
    non_name_morphs: list[Morpheme] = []

    for morph in morphs:
        if morph.inflection not in names:
            non_name_morphs.append(morph)

    return non_name_morphs
