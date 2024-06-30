from collections.abc import Iterator
from test.fake_environment_module import FakeEnvironment
from unittest import mock

import pytest

import ankimorphs.morphemizers.morphemizer
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizers import spacy_wrapper
from ankimorphs.morphemizers.morphemizer import get_morphemizer_by_description


@pytest.fixture(scope="function")
def fake_environment() -> Iterator[None]:
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )
    patch_testing_variable.start()
    yield
    patch_testing_variable.stop()
    # this resets the morphemizers for the future tests
    # todo: refactor this to be more palatable
    ankimorphs.morphemizers.morphemizer.morphemizers = None


def test_french(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
) -> None:
    morphemizer = get_morphemizer_by_description("AnkiMorphs: Language w/ Spaces")
    assert morphemizer is not None

    sentence = "Tu es quelqu'un de bien."
    correct_morphs: set[Morpheme] = {
        Morpheme("tu", "tu"),
        Morpheme("es", "es"),
        Morpheme("quelqu'un", "quelqu'un"),
        Morpheme("de", "de"),
        Morpheme("bien", "bien"),
    }

    extracted_morphs = morphemizer.get_morphemes_from_expr(sentence)
    assert len(extracted_morphs) == 5

    for morph in extracted_morphs:
        assert morph in correct_morphs


def test_english(  # pylint:disable=unused-argument
    fake_environment: FakeEnvironment,
) -> None:
    morphemizer = get_morphemizer_by_description("AnkiMorphs: Language w/ Spaces")
    assert morphemizer is not None

    sentence = "My mother-in-law is wonderful"
    correct_morphs: set[Morpheme] = {
        Morpheme("my", "my"),
        Morpheme("mother-in-law", "mother-in-law"),
        Morpheme("is", "is"),
        Morpheme("wonderful", "wonderful"),
    }

    extracted_morphs = morphemizer.get_morphemes_from_expr(sentence)
    assert len(extracted_morphs) == 4

    for morph in extracted_morphs:
        assert morph in correct_morphs
