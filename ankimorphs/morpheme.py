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
        self.pos = pos  # determined by mecab tool. for example: u'動詞' or u'助動詞', u'形容詞'
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


class SimplifiedMorph:
    __slots__ = (
        "norm",
        "inflected",
        "highest_learning_interval",
        "norm_and_inflected",
    )

    def __init__(
        self, norm: str, inflected: str, highest_learning_interval: int
    ) -> None:
        self.norm: str = norm
        self.inflected: str = inflected
        self.highest_learning_interval: int = highest_learning_interval
        self.norm_and_inflected: str = self.norm + self.inflected
