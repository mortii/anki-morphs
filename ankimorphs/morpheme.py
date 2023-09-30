from ankimorphs.config import get_config as cfg


def char_set(start: str, end: str) -> set:
    return {chr(_char) for _char in range(ord(start), ord(end) + 1)}


kanji_chars = char_set("㐀", "䶵") | char_set("一", "鿋") | char_set("豈", "頻")


class Morpheme:
    def __init__(  # pylint:disable=too-many-arguments
        self, norm, base, inflected, read, pos, sub_pos
    ):
        """Initialize morpheme class.

        POS means part-of-speech.

        Example morpheme infos for the expression "歩いて":

        :param str norm: 歩く [normalized base form]
        :param str base: 歩く
        :param str inflected: 歩い  [mecab cuts off all endings, so there is not て]
        :param str read: アルイ
        :param str pos: 動詞
        :param str sub_pos: 自立

        """
        # values are created by "mecab" in the order of the parameters and then directly passed into this constructor
        # example of mecab output:    "歩く     歩い    動詞    自立      アルイ"
        # matches to:                 "base     infl    pos     subPos    read"
        self.norm = norm if norm is not None else base
        self.base = base
        self.inflected = inflected
        self.read = read
        self.pos = pos  # type of morpheme determined by mecab tool. for example: u'動詞' or u'助動詞', u'形容詞'
        self.sub_pos = sub_pos

    def __setstate__(self, data):
        """Override default pickle __setstate__ to initialize missing defaults in old databases"""
        self.norm = data["norm"] if "norm" in data else data["base"]
        self.base = data["base"]
        self.inflected = data["inflected"]
        self.read = data["read"]
        self.pos = data["pos"]
        self.sub_pos = data["sub_pos"]

    def __eq__(self, other):
        return all(
            [
                isinstance(other, Morpheme),
                self.norm == other.norm,
                self.base == other.base,
                self.inflected == other.inflected,
                self.read == other.read,
                self.pos == other.pos,
                self.sub_pos == other.sub_pos,
            ]
        )

    def __hash__(self):
        return hash(
            (self.norm, self.base, self.inflected, self.read, self.pos, self.sub_pos)
        )

    def base_kanji(self) -> set:
        # todo: profile and maybe cache
        return set(self.base) & kanji_chars

    def get_group_key(self) -> str:
        if cfg("Option_IgnoreGrammarPosition"):
            return f"{self.norm}\t{self.read}"
        return f"{self.norm}\t{self.read}\t{self.pos}\t"

    def is_proper_noun(self):
        return self.sub_pos == "固有名詞" or self.pos == "PROPN"

    def show(self):  # str
        return "\t".join(
            [self.norm, self.base, self.inflected, self.read, self.pos, self.sub_pos]
        )

    def deinflected(self):
        if self.inflected == self.base:
            return self
        return Morpheme(
            self.norm, self.base, self.base, self.read, self.pos, self.sub_pos
        )
