import os
import sys
from unittest import mock

import pytest

from ankimorphs import spacy_wrapper
from ankimorphs.morpheme import Morpheme
from ankimorphs.morphemizer import get_morphemizer_by_name


@pytest.fixture(
    scope="module"  # module-scope: created and destroyed once per module. Cached.
)
def fake_environment():
    patch_testing_variable = mock.patch.object(
        spacy_wrapper, "testing_environment", True
    )

    tests_path = os.path.join(os.path.abspath("tests"), "data")
    fake_morphemizers_path = os.path.join(tests_path, "morphemizers")

    sys.path.append(fake_morphemizers_path)
    patch_testing_variable.start()
    yield
    patch_testing_variable.stop()
    sys.path.remove(fake_morphemizers_path)


@pytest.mark.external_morphemizers
def test_morpheme_generation(fake_environment):  # pylint:disable=unused-argument
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
