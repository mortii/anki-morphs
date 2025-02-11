from __future__ import annotations

from ..morphemizers import spacy_wrapper
from ..morphemizers.jieba_morphemizer import JiebaMorphemizer
from ..morphemizers.mecab_morphemizer import MecabMorphemizer
from ..morphemizers.morphemizer import Morphemizer
from ..morphemizers.simple_space_morphemizer import SimpleSpaceMorphemizer
from ..morphemizers.spacy_morphemizer import SpacyMorphemizer

available_morphemizers: list[Morphemizer] | None = None
morphemizers_by_description: dict[str, Morphemizer] = {}


def get_all_morphemizers() -> list[Morphemizer]:
    global available_morphemizers

    if available_morphemizers is None:
        # the space morphemizer is always included since it's pure python
        available_morphemizers = [
            SimpleSpaceMorphemizer(),
        ]

        _mecab = MecabMorphemizer()
        if _mecab.init_successful():
            available_morphemizers.append(_mecab)

        _jieba = JiebaMorphemizer()
        if _jieba.init_successful():
            available_morphemizers.append(_jieba)

        spacy_wrapper.load_spacy_modules()
        for spacy_model in spacy_wrapper.get_installed_models():
            available_morphemizers.append(SpacyMorphemizer(spacy_model))

        # update the 'names to morphemizers' dict while we are at it
        for morphemizer in available_morphemizers:
            morphemizers_by_description[morphemizer.get_description()] = morphemizer

    return available_morphemizers


def get_morphemizer_by_description(description: str) -> Morphemizer | None:
    get_all_morphemizers()
    return morphemizers_by_description.get(description, None)
