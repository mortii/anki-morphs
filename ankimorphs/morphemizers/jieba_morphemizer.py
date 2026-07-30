from collections.abc import Iterator

from ..morpheme import Morpheme
from ..morphemizers.morphemizer import Morphemizer
from . import jieba_wrapper


class JiebaMorphemizer(Morphemizer):
    # Jieba Chinese text segmentation: https://github.com/fxsjy/jieba

    def __init__(self) -> None:
        super().__init__()
        jieba_wrapper.import_jieba()

    def init_successful(self) -> bool:
        return jieba_wrapper.successful_import

    def get_morphemes(
        self, items: list[tuple[str, int]]
    ) -> Iterator[tuple[list[Morpheme], int]]:
        for sentence, key in items:
            yield jieba_wrapper.get_morphemes_jieba(sentence), key

    def get_description(self) -> str:
        return "AnkiMorphs: Chinese"
