from ankimorphs.morphemizer import get_morphemizer_by_name


def test_morpheme_generation_space():
    morphemizer = get_morphemizer_by_name("SpaceMorphemizer")

    sentence_1 = "Tu es quelqu'un de bien."
    case_1 = "tu es quelqu'un de bien"

    sentence_2 = "El griego antiguo es el lenguaje de las obras de Homero, incluyendo la Ilíada y la Odisea."
    case_2 = "el griego antiguo es el lenguaje de las obras de homero incluyendo la ilíada y la odisea"

    sentence_3 = "MorphMan is an Anki addon that tracks what words you know, and utilizes that information to optimally reorder language cards."
    case_3 = "morphman is an anki addon that tracks what words you know and utilizes that information to optimally reorder language cards"

    sentence_4 = "The Mass Immersion Approach is a comprehensive approach to acquiring foreign languages."
    case_4 = "the mass immersion approach is a comprehensive approach to acquiring foreign languages"

    for idx, morph in enumerate(morphemizer.get_morphemes_from_expr(sentence_1)):
        assert morph.base == case_1.split(" ")[idx]

    for idx, morph in enumerate(morphemizer.get_morphemes_from_expr(sentence_2)):
        assert morph.base == case_2.split(" ")[idx]

    for idx, morph in enumerate(morphemizer.get_morphemes_from_expr(sentence_3)):
        assert morph.base == case_3.split(" ")[idx]

    for idx, morph in enumerate(morphemizer.get_morphemes_from_expr(sentence_4)):
        assert morph.base == case_4.split(" ")[idx]
