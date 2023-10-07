import re

from .config import AnkiMorphsConfig
from .morpheme import Morpheme
from .morphemizer import Morphemizer


def ms2str(morphs):  # [(Morpheme, locs)] -> Str
    return "\n".join(
        [
            "%d\t%s"  # pylint:disable=consider-using-f-string
            % (len(m[1]), m[0].show())
            for m in morphs
        ]
    )


def get_morphemes(
    morphemizer: Morphemizer, expression, am_config: AnkiMorphsConfig, note_tags=None
) -> list[Morpheme]:
    expression = replace_bracket_contents(expression, am_config)
    morphs = morphemizer.get_morphemes_from_expr(expression)
    return morphs


square_brackets_regex = re.compile(r"\[[^\]]*\]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^\)]*\)")


def replace_bracket_contents(expression, am_config: AnkiMorphsConfig):
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
