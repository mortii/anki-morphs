import functools
import os
import re

from aqt import mw

from .config import AnkiMorphsConfig
from .morpheme import Morpheme
from .morphemizer import Morphemizer

square_brackets_regex = re.compile(r"\[[^\]]*\]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^\)]*\)")


def get_morphemes(
    morphemizer: Morphemizer, expression: str, am_config: AnkiMorphsConfig
) -> list[Morpheme]:
    expression = _get_parsed_expression(expression, am_config)
    morphs = morphemizer.get_morphemes_from_expr(expression)
    names_set = create_hash_set_out_of_names()
    morphs = list(filter(lambda x: (x.inflected not in names_set), morphs))
    return morphs


def _get_parsed_expression(expression: str, am_config: AnkiMorphsConfig) -> str:
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


@functools.cache
def create_hash_set_out_of_names() -> set[str]:
    if mw is not None:
        profile_path = mw.pm.profileFolder()
    else:
        return set()
    path: str = os.path.join(profile_path, "names.txt")
    with open(path, encoding="utf-8") as names_file:
        lines_lower_case = map(lambda x: x.lower(), names_file.read().splitlines())
        hashset = set(lines_lower_case)
        return hashset
