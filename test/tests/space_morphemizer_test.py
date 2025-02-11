from collections.abc import Iterator
from unittest import mock

import pytest

import ankimorphs.morphemizers.morphemizer
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.morphemizers.morphemizer_utils import get_morphemizer_by_description


@pytest.fixture(scope="function")
def _fake_environment_fixture() -> Iterator[None]:
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )
    patch_testing_variable.start()
    yield
    patch_testing_variable.stop()
    # this resets the morphemizers for the future tests
    ankimorphs.morphemizers.morphemizer_utils.available_morphemizers = None


@pytest.mark.parametrize(
    "morphemizer_description, sentence, correct_morphs",
    [
        (
            "AnkiMorphs: Simple Space Splitter",
            "Tu es quelqu'un de bien",  # french test
            {
                Morpheme("tu", "tu"),
                Morpheme("es", "es"),
                Morpheme("quelqu'un", "quelqu'un"),
                Morpheme("de", "de"),
                Morpheme("bien", "bien"),
            },
        ),
        (
            "AnkiMorphs: Simple Space Splitter",
            "My mother-in-law is wonderful",  # english test
            {
                Morpheme("my", "my"),
                Morpheme("mother-in-law", "mother-in-law"),
                Morpheme("is", "is"),
                Morpheme("wonderful", "wonderful"),
            },
        ),
        (
            "AnkiMorphs: Simple Space Splitter",
            "أنا بصدّقك وإحنا دايماً منقلكم",  # arabic test
            {
                Morpheme("منقلكم", "منقلكم"),
                Morpheme("دايماً", "دايماً"),
                Morpheme("وإحنا", "وإحنا"),
                Morpheme("بصدّقك", "بصدّقك"),
                Morpheme("أنا", "أنا"),
            },
        ),
    ],
)
def test_simple_space_splitters(
    _fake_environment_fixture: None,
    morphemizer_description: str,
    sentence: str,
    correct_morphs: set[Morpheme],
) -> None:
    morphemizer = get_morphemizer_by_description(morphemizer_description)
    assert morphemizer is not None

    extracted_morphs = next(morphemizer.get_morphemes([sentence]))
    assert len(extracted_morphs) == len(correct_morphs)

    for morph in extracted_morphs:
        # print(f"morph: {morph.inflection}")
        assert morph in correct_morphs
