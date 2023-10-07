import re

from ankimorphs.config import AnkiMorphsConfig
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import Morphemizer


def get_morphemes(
    morphemizer: Morphemizer, expression: str, am_config: AnkiMorphsConfig
) -> list[Morpheme]:
    expression = _replace_bracket_contents(expression, am_config)
    morphs = morphemizer.get_morphemes_from_expr(expression)
    return morphs


square_brackets_regex = re.compile(r"\[[^\]]*\]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^\)]*\)")


def _replace_bracket_contents(expression: str, am_config: AnkiMorphsConfig) -> str:
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


def alt_includes_morpheme(morph: Morpheme, alt: Morpheme) -> bool:
    return morph.norm == alt.norm and (
        morph.base == alt.base or morph.base_kanji() <= alt.base_kanji()
    )
