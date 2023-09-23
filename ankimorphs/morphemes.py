import pickle
import re
from abc import ABC, abstractmethod

from .exceptions import ProfileNotYetLoadedException
from .morpheme import Morpheme


def error_msg(msg):
    pass


try:
    from .preferences import get_preference as cfg
except ProfileNotYetLoadedException:

    def cfg(config_string):
        return None


def ms2str(morphs):  # [(Morpheme, locs)] -> Str
    return "\n".join(
        [
            "%d\t%s"  # pylint:disable=consider-using-f-string
            % (len(m[1]), m[0].show())
            for m in morphs
        ]
    )


class MorphDBUnpickler(pickle.Unpickler):
    def find_class(self, cmodule, cname):
        # Override default class lookup for this module to allow loading databases generated with older
        # versions of the MorphMan add-on.
        if cmodule.endswith("morphemes"):
            return globals()[cname]
        return pickle.Unpickler.find_class(self, cmodule, cname)


def get_morphemes(morphemizer, expression, note_tags=None):
    expression = replace_bracket_contents(expression)

    # go through all replacement rules and search if a rule (which dictates a string to morpheme conversion) can be
    # applied
    replace_rules = cfg("ReplaceRules")
    # NB: replace_rules is by default just an empty list...

    if note_tags is not None and replace_rules is not None:
        note_tags_set = set(note_tags)
        for filter_tags, regex, morphemes in replace_rules:
            if not set(filter_tags) <= note_tags_set:
                continue

            # find matches
            split_expression = re.split(regex, expression, maxsplit=1, flags=re.UNICODE)

            if len(split_expression) == 1:
                continue  # no match
            assert len(split_expression) == 2

            # make sure this rule doesn't lead to endless recursion
            if len(split_expression[0]) >= len(expression) or len(
                split_expression[1]
            ) >= len(expression):
                continue

            a_morphs = get_morphemes(morphemizer, split_expression[0], note_tags)
            b_morphs = [
                Morpheme(mstr, mstr, mstr, mstr, "UNKNOWN", "UNKNOWN")
                for mstr in morphemes
            ]
            c_morphs = get_morphemes(morphemizer, split_expression[1], note_tags)
            return a_morphs + b_morphs + c_morphs

    morphs = morphemizer.get_morphemes_from_expr(expression)

    return morphs


square_brackets_regex = re.compile(r"\[[^\]]*\]")
round_brackets_regex = re.compile(r"（[^）]*）")
slim_round_brackets_regexp = re.compile(r"\([^\)]*\)")


def replace_bracket_contents(expression):
    if cfg("Option_IgnoreBracketContents"):
        if square_brackets_regex.search(expression):
            expression = square_brackets_regex.sub("", expression)

    if cfg("Option_IgnoreRoundBracketContents"):
        if round_brackets_regex.search(expression):
            expression = round_brackets_regex.sub("", expression)

    if cfg("Option_IgnoreSlimRoundBracketContents"):
        if slim_round_brackets_regexp.search(expression):
            expression = slim_round_brackets_regexp.sub("", expression)

    return expression


class Location(ABC):
    def __init__(self, weight):
        self.weight = weight
        self.maturity = 0

    @abstractmethod
    def show(self):
        pass


class Nowhere(Location):
    def __init__(self, tag, weight=0):
        super().__init__(weight)
        self.tag = tag

    def show(self):
        return f"{self.tag}@{self.maturity}"


class Corpus(Location):
    """A corpus we want to use for priority, without storing more than morpheme frequencies."""

    def __init__(self, name, weight):
        super().__init__(weight)
        self.name = name

    def show(self):
        return f"{self.name}*{self.weight}@{self.maturity}"


class TextFile(Location):
    def __init__(self, file_path, line_no, maturity, weight=1):
        super().__init__(weight)
        self.file_path = file_path
        self.line_num = line_no
        self.maturity = maturity

    def show(self):
        return f"{self.file_path}:{self.line_num}@{self.maturity}"


class AnkiDeck(Location):
    """This maps to/contains information for one note and one relevant field like u'Expression'."""

    def __init__(  # pylint:disable=too-many-arguments
        self, note_id, field_name, field_value, guid, maturity, weight=1
    ):
        super().__init__(weight)
        self.note_id = note_id
        self.field_name = field_name  # for example u'Expression'
        self.field_value = field_value  # for example u'それだけじゃない'
        self.guid = guid
        # list of intergers, one for every card -> containg the intervals of every card for this note
        self.maturities = None
        self.maturity = maturity
        self.weight = weight

    def show(self):
        return f"{self.note_id}[{self.field_name}]@{self.maturity}"


def alt_includes_morpheme(morph: Morpheme, alt: Morpheme) -> bool:
    return morph.norm == alt.norm and (
        morph.base == alt.base or morph.base_kanji() <= alt.base_kanji()
    )
