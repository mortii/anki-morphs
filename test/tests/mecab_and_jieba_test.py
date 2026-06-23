from test.fake_environment_module import (  # pylint:disable=unused-import
    fake_environment_fixture,
)

import pytest

from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizers.morphemizer_utils import get_morphemizer_by_description


@pytest.mark.mecab
def test_mecab_morpheme_generation(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    morphemizer = get_morphemizer_by_description("AnkiMorphs: Japanese")
    assert morphemizer is not None

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

    extracted_morphs = next(morphemizer.get_morphemes([sentence]))
    assert len(extracted_morphs) == 9

    for morph in extracted_morphs:
        assert morph in correct_morphs


@pytest.mark.jieba
def test_jieba_morpheme_generation(  # pylint:disable=unused-argument
    fake_environment_fixture: None,
) -> None:
    morphemizer = get_morphemizer_by_description("AnkiMorphs: Chinese")
    assert morphemizer is not None

    sentence = "请您说得慢些好吗？"
    correct_morphs: set[Morpheme] = {
        Morpheme("吗", "吗"),
        Morpheme("好", "好"),
        Morpheme("得", "得"),
        Morpheme("您", "您"),
        Morpheme("慢些", "慢些"),
        Morpheme("说", "说"),
        Morpheme("请", "请"),
    }

    extracted_morphs = next(morphemizer.get_morphemes([sentence]))
    assert len(extracted_morphs) == 7

    for morph in extracted_morphs:
        assert morph in correct_morphs

    sentence = "一，二，三，跳！"
    correct_morphs = {
        Morpheme("一", "一"),
        Morpheme("二", "二"),
        Morpheme("三", "三"),
        Morpheme("跳", "跳"),
    }

    extracted_morphs = next(morphemizer.get_morphemes([sentence]))
    assert len(extracted_morphs) == 4

    for morph in extracted_morphs:
        assert morph in correct_morphs
