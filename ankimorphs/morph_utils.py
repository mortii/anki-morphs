import re

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


def alt_includes_morpheme(morph: Morpheme, alt: Morpheme) -> bool:
    return morph.norm == alt.norm and (
        morph.base == alt.base or morph.base_kanji() <= alt.base_kanji()
    )
