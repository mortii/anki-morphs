from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


def test_morpheme_generation():
    morphemizer = get_morphemizer_by_name("MecabMorphemizer")

    sentence = "本当に重要な任務の時しか 動かない"
    correct_morphs: set[Morpheme] = {
        Morpheme("本当に", "本当に"),
        Morpheme("重要", "重要"),
        Morpheme("だ", "な"),
        Morpheme("任務", "任務"),
        Morpheme("の", "の"),
        Morpheme("時", "時"),
        Morpheme("しか", "しか"),
        Morpheme("動く", "動か"),
        Morpheme("ない", "ない"),
    }

    extracted_morphs = morphemizer.get_morphemes_from_expr(sentence)
    assert len(extracted_morphs) == 9

    for morph in extracted_morphs:
        assert morph in correct_morphs
