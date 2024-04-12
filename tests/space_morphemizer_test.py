from unittest import mock

import pytest

import ankimorphs.morphemizer
from ankimorphs import spacy_wrapper
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_description


@pytest.fixture(scope="function")
def fake_environment():
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )
    patch_testing_variable.start()
    yield
    patch_testing_variable.stop()
    # this resets the morphemizers for the future tests
    ankimorphs.morphemizer.morphemizers = None


def test_french(fake_environment):  # pylint:disable=unused-argument
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


def test_english(fake_environment):  # pylint:disable=unused-argument
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
