import re

from . import name_file_utils
from .config import AnkiMorphsConfig
from .morpheme import Morpheme
from .morphemizer import Morphemizer

square_brackets_regex = re.compile(r"\[[^]]*]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^)]*\)")
non_alpha_regexp = re.compile(r"[-'\w]")


def get_processed_spacy_morphs(am_config: AnkiMorphsConfig, doc) -> set[Morpheme]:  # type: ignore[no-untyped-def]
    # doc: spacy.tokens.Doc

    morphs: set[Morpheme] = set()

    for w in doc:
        # print(f"w: {w}")
        if not non_alpha_regexp.search(w.text):
            continue

        if am_config.preprocess_ignore_names_morphemizer:
            if w.pos == 96:  # PROPN
                continue

        morphs.add(
            Morpheme(
                base=w.lemma_,
                inflected=w.text,
            )
        )

    if am_config.preprocess_ignore_names_textfile:
        morphs = remove_names_textfile(morphs)

    return morphs


def get_processed_morphemizer_morphs(
    morphemizer: Morphemizer, expression: str, am_config: AnkiMorphsConfig
) -> set[Morpheme]:
    morphs: set[Morpheme] = morphemizer.get_morphemes_from_expr(expression)

    if am_config.preprocess_ignore_names_morphemizer:
        morphs = remove_names_morphemizer(morphs)

    if am_config.preprocess_ignore_names_textfile:
        morphs = remove_names_textfile(set(morphs))

    return morphs


def get_processed_expression(am_config: AnkiMorphsConfig, expression: str) -> str:
    if am_config.preprocess_ignore_bracket_contents:
        if square_brackets_regex.search(expression):
            expression = square_brackets_regex.sub("", expression)

    if am_config.preprocess_ignore_round_bracket_contents:
        if round_brackets_regex.search(expression):
            expression = round_brackets_regex.sub("", expression)

    if am_config.preprocess_ignore_slim_round_bracket_contents:
        if slim_round_brackets_regexp.search(expression):
            expression = slim_round_brackets_regexp.sub("", expression)

    return expression


def remove_names_morphemizer(morphs: set[Morpheme]) -> set[Morpheme]:
    return {morph for morph in morphs if not morph.is_proper_noun()}


def remove_names_textfile(morphs: set[Morpheme]) -> set[Morpheme]:
    names = name_file_utils.get_names_from_file()
    non_name_morphs: set[Morpheme] = set()

    for morph in morphs:
        if morph.inflected not in names:
            non_name_morphs.add(morph)

    return non_name_morphs
