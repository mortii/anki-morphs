import re

from . import name_file_utils
from .config import AnkiMorphsConfig
from .morpheme import Morpheme
from .morphemizer import Morphemizer

square_brackets_regex = re.compile(r"\[[^]]*]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^)]*\)")


def get_morphemes(
    morphemizer: Morphemizer, expression: str, am_config: AnkiMorphsConfig
) -> list[Morpheme]:
    expression = _get_parsed_expression(am_config, expression)
    morphs = morphemizer.get_morphemes_from_expr(expression)

    if am_config.parse_ignore_names_morphemizer:
        morphs = remove_names_morphemizer(morphs)

    if am_config.parse_ignore_names_textfile:
        morphs = remove_names_textfile(morphs)

    return morphs


def _get_parsed_expression(am_config: AnkiMorphsConfig, expression: str) -> str:
    if am_config.parse_ignore_bracket_contents:
        if square_brackets_regex.search(expression):
            expression = square_brackets_regex.sub("", expression)

    if am_config.parse_ignore_round_bracket_contents:
        if round_brackets_regex.search(expression):
            expression = round_brackets_regex.sub("", expression)

    if am_config.parse_ignore_slim_round_bracket_contents:
        if slim_round_brackets_regexp.search(expression):
            expression = slim_round_brackets_regexp.sub("", expression)

    return expression


def remove_names_textfile(morphs: list[Morpheme]) -> list[Morpheme]:
    names = name_file_utils.get_names_from_file()
    non_name_morphs: list[Morpheme] = []

    for morph in morphs:
        if morph.inflected not in names:
            non_name_morphs.append(morph)

    return non_name_morphs


def remove_names_morphemizer(morphs: list[Morpheme]) -> list[Morpheme]:
    return [morph for morph in morphs if not morph.is_proper_noun()]
