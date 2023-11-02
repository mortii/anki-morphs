import functools
import os
import re

from aqt import mw

from .config import AnkiMorphsConfig
from .exceptions import NamesTextfileNotFoundException
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
    morphs = _remove_names(am_config, morphs)
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

    if am_config.parse_ignore_quotation_marks:
        # replace quotation marks with a whitespace
        expression = re.sub('["«»]', " ", expression)

    return expression


def _remove_names(
    am_config: AnkiMorphsConfig, morphs: list[Morpheme]
) -> list[Morpheme]:
    if not am_config.parse_ignore_names_textfile:
        return morphs

    names = create_hash_set_out_of_names()
    non_name_morphs: list[Morpheme] = []

    for morph in morphs:
        if morph.inflected not in names:
            non_name_morphs.append(morph)

    return non_name_morphs


@functools.cache
def create_hash_set_out_of_names() -> set[str]:
    assert mw is not None

    profile_path: str = mw.pm.profileFolder()
    path: str = os.path.join(profile_path, "names.txt")

    try:
        with open(path, encoding="utf-8") as names_file:
            lines_lower_case = map(lambda x: x.lower(), names_file.read().splitlines())
            names = set(lines_lower_case)
    except FileNotFoundError as error:
        raise NamesTextfileNotFoundException(path) from error

    return names
