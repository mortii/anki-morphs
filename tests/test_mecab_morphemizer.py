from ankimorphs.morphemizer import get_morphemizer_by_name


def test_morpheme_generation():
    morphemizer = get_morphemizer_by_name("MecabMorphemizer")

    sentence_1 = "こんにちは。私の名前はシャンです。"
    case_1 = ["こんにちは", "私", "の", "名前", "は", "シャン", "です"]

    for idx, morph in enumerate(morphemizer.get_morphemes_from_expr(sentence_1)):
        assert morph.base == case_1[idx]
