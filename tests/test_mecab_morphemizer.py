from ankimorphs.morphemizer import getMorphemizerByName


def test_morpheme_generation():
    morphemizer = getMorphemizerByName("MecabMorphemizer")

    sentence_1 = "こんにちは。私の名前はシャンです。"
    case_1 = ["こんにちは", "私", "の", "名前", "は", "シャン", "です"]

    for idx, m in enumerate(morphemizer.getMorphemesFromExpr(sentence_1)):
        assert m.base == case_1[idx]
