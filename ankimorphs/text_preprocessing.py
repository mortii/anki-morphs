import re
from typing import Any

from . import name_file_utils
from .ankimorphs_config import AnkiMorphsConfig
from .morpheme import Morpheme
from .morphemizers.morphemizer import Morphemizer

square_brackets_regex = re.compile(r"\[[^]]*]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^)]*\)")
non_alpha_regexp = re.compile(r"[-'\w]")
ruby_regex = re.compile(r" ?([^] \W]+)\[(.+?)\]")

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

    if am_config.preprocess_ignore_custom_characters:
        # str.translate() removes characters in a single pass, which is
        # much more efficient than str.replace()
        text = text.translate(translation_table)

    return text


def get_processed_spacy_morphs(am_config: AnkiMorphsConfig, doc: Any) -> list[Morpheme]:
    # doc: spacy.tokens.Doc

    morphs: list[Morpheme] = []

    for w in doc:
        if not non_alpha_regexp.search(w.text):
            continue

        if am_config.preprocess_ignore_names_morphemizer:
            if w.pos == 96:  # PROPN
                continue

        morphs.append(
            Morpheme(
                lemma=w.lemma_,
                inflection=w.text,
            )
        )

    if am_config.preprocess_ignore_names_textfile:
        morphs = remove_names_textfile(morphs)

    return morphs


def get_processed_morphemizer_morphs(
    morphemizer: Morphemizer, text: str, am_config: AnkiMorphsConfig
) -> list[Morpheme]:
    morphs: list[Morpheme] = morphemizer.get_morphemes_from_expr(text)

    if am_config.preprocess_ignore_names_morphemizer:
        morphs = remove_names_morphemizer(morphs)

    if am_config.preprocess_ignore_names_textfile:
        morphs = remove_names_textfile(morphs)

    return morphs


def remove_names_morphemizer(morphs: list[Morpheme]) -> list[Morpheme]:
    return [morph for morph in morphs if not morph.is_proper_noun()]


def remove_names_textfile(morphs: list[Morpheme]) -> list[Morpheme]:
    names = name_file_utils.get_names_from_file()
    non_name_morphs: list[Morpheme] = []

    for morph in morphs:
        if morph.inflection not in names:
            non_name_morphs.append(morph)

    return non_name_morphs
