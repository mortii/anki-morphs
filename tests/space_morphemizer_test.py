from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


def test_french():
    morphemizer = get_morphemizer_by_name("SpaceMorphemizer")

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


def test_english():
    morphemizer = get_morphemizer_by_name("SpaceMorphemizer")

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
